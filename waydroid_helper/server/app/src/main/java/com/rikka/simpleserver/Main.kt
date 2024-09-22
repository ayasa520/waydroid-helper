package com.rikka.simpleserver

import android.os.Build
import android.os.SystemClock
import android.view.InputDevice
import android.view.KeyCharacterMap
import android.view.MotionEvent
import android.view.MotionEvent.PointerCoords
import android.view.MotionEvent.PointerProperties
import com.rikka.simpleserver.wrappers.InputManager
import io.ktor.network.selector.SelectorManager
import io.ktor.network.sockets.aSocket
import io.ktor.network.sockets.openReadChannel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readFully
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import java.nio.ByteBuffer
import java.nio.ByteOrder


enum class ControlMsgType(val value: Byte) {
    INJECT_KEYCODE(0),
    INJECT_TEXT(1),
    INJECT_TOUCH_EVENT(2),
    INJECT_SCROLL_EVENT(3),
    // ... 其他类型
}

data class ControlMsg(val type: ControlMsgType, val data: ByteArray)

class Controller(
    private val device: Device,
    private val charMap: KeyCharacterMap? = KeyCharacterMap.load(KeyCharacterMap.VIRTUAL_KEYBOARD),
    private var lastTouchDown: Long = 0,
    private val pointersState: PointersState = PointersState(),
    private val pointerProperties: Array<PointerProperties?> = arrayOfNulls<PointerProperties>(
        PointersState.MAX_POINTERS
    ),
    private val pointerCoords: Array<PointerCoords?> = arrayOfNulls<PointerCoords>(PointersState.MAX_POINTERS),
) {
    companion object {
        private const val DEFAULT_DEVICE_ID = 0

        // control_msg.h values of the pointerId field in inject_touch_event message
        private const val POINTER_ID_MOUSE = -1L
        private const val POINTER_ID_VIRTUAL_MOUSE = -3L
    }

    init {
        initPointers()
    }

    private fun initPointers() {
        for (i in 0 until PointersState.MAX_POINTERS) {
            val props = PointerProperties()
            props.toolType = MotionEvent.TOOL_TYPE_FINGER

            val coords = PointerCoords()
            coords.orientation = 0f
            coords.size = 0f

            pointerProperties[i] = props
            pointerCoords[i] = coords
        }
    }

    private fun injectKeycode(action: Int, keycode: Int, repeat: Int, metaState: Int): Boolean {
        return device.injectKeyEvent(action, keycode, repeat, metaState, Device.INJECT_MODE_ASYNC)
    }

    private fun injectTouch(
        action: Int,
        pointerId: Long,
        position: Position,
        pressure: Float,
        actionButton: Int,
        buttons: Int
    ): Boolean {
        var action = action
        var buttons = buttons
        val now = SystemClock.uptimeMillis()

        val point = device.getPhysicalPoint(position)
        if (point == null) {
            Ln.w("Ignore touch event, it was generated for a different device size")
            return false
        }

        val pointerIndex = pointersState.getPointerIndex(pointerId)
        if (pointerIndex == -1) {
            Ln.w("Too many pointers for touch event")
            return false
        }
        val pointer = pointersState[pointerIndex]
        pointer.point = point
        pointer.pressure = pressure

        val source: Int
        val activeSecondaryButtons =
            ((actionButton or buttons) and MotionEvent.BUTTON_PRIMARY.inv()) != 0
        if (pointerId == POINTER_ID_MOUSE && (action == MotionEvent.ACTION_HOVER_MOVE || activeSecondaryButtons)) {
            // real mouse event, or event incompatible with a finger
            pointerProperties[pointerIndex]!!.toolType = MotionEvent.TOOL_TYPE_MOUSE
            source = InputDevice.SOURCE_MOUSE
            pointer.isUp = buttons == 0
        } else {
            // POINTER_ID_GENERIC_FINGER, POINTER_ID_VIRTUAL_FINGER or real touch from device
            pointerProperties[pointerIndex]!!.toolType = MotionEvent.TOOL_TYPE_FINGER
            source = InputDevice.SOURCE_TOUCHSCREEN
            // Buttons must not be set for touch events
            buttons = 0
            pointer.isUp = action == MotionEvent.ACTION_UP
        }

        val pointerCount = pointersState.update(pointerProperties, pointerCoords)
        if (pointerCount == 1) {
            if (action == MotionEvent.ACTION_DOWN) {
                lastTouchDown = now
            }
        } else {
            // secondary pointers must use ACTION_POINTER_* ORed with the
            if (action == MotionEvent.ACTION_UP) {
                action =
                    MotionEvent.ACTION_POINTER_UP or (pointerIndex shl MotionEvent.ACTION_POINTER_INDEX_SHIFT)
            } else if (action == MotionEvent.ACTION_DOWN) {
                action =
                    MotionEvent.ACTION_POINTER_DOWN or (pointerIndex shl MotionEvent.ACTION_POINTER_INDEX_SHIFT)
            }
        }

        /* If the input device is a mouse (on API >= 23):
         *   - the first button pressed must first generate ACTION_DOWN;
         *   - all button pressed (including the first one) must generate ACTION_BUTTON_PRESS;
         *   - all button released (including the last one) must generate ACTION_BUTTON_RELEASE;
         *   - the last button released must in addition generate ACTION_UP.
         *
         * Otherwise, Chrome does not work properly: <https://github.com/Genymobile/scrcpy/issues/3635>
         */
        if (source == InputDevice.SOURCE_MOUSE) {
            if (action == MotionEvent.ACTION_DOWN) {
                if (actionButton == buttons) {
                    // First button pressed: ACTION_DOWN
                    val downEvent = MotionEvent.obtain(
                        lastTouchDown,
                        now,
                        MotionEvent.ACTION_DOWN,
                        pointerCount,
                        pointerProperties,
                        pointerCoords,
                        0,
                        buttons,
                        1f,
                        1f,
                        DEFAULT_DEVICE_ID,
                        0,
                        source,
                        0
                    )
                    if (!device.injectEvent(downEvent, Device.INJECT_MODE_ASYNC)) {
                        return false
                    }
                }

                // Any button pressed: ACTION_BUTTON_PRESS
                val pressEvent = MotionEvent.obtain(
                    lastTouchDown,
                    now,
                    MotionEvent.ACTION_BUTTON_PRESS,
                    pointerCount,
                    pointerProperties,
                    pointerCoords,
                    0,
                    buttons,
                    1f,
                    1f,
                    DEFAULT_DEVICE_ID,
                    0,
                    source,
                    0
                )
                if (!InputManager.setActionButton(pressEvent, actionButton)) {
                    return false
                }
                if (!device.injectEvent(pressEvent, Device.INJECT_MODE_ASYNC)) {
                    return false
                }

                return true
            }

            if (action == MotionEvent.ACTION_UP) {
                // Any button released: ACTION_BUTTON_RELEASE
                val releaseEvent = MotionEvent.obtain(
                    lastTouchDown,
                    now,
                    MotionEvent.ACTION_BUTTON_RELEASE,
                    pointerCount,
                    pointerProperties,
                    pointerCoords,
                    0,
                    buttons,
                    1f,
                    1f,
                    DEFAULT_DEVICE_ID,
                    0,
                    source,
                    0
                )
                if (!InputManager.setActionButton(releaseEvent, actionButton)) {
                    return false
                }
                if (!device.injectEvent(releaseEvent, Device.INJECT_MODE_ASYNC)) {
                    return false
                }

                if (buttons == 0) {
                    // Last button released: ACTION_UP
                    val upEvent = MotionEvent.obtain(
                        lastTouchDown, now, MotionEvent.ACTION_UP, pointerCount, pointerProperties,
                        pointerCoords, 0, buttons, 1f, 1f, DEFAULT_DEVICE_ID, 0, source, 0
                    )
                    if (!device.injectEvent(upEvent, Device.INJECT_MODE_ASYNC)) {
                        return false
                    }
                }

                return true
            }
        }

        val event = MotionEvent.obtain(
            lastTouchDown,
            now,
            action,
            pointerCount,
            pointerProperties,
            pointerCoords,
            0,
            buttons,
            1f,
            1f,
            DEFAULT_DEVICE_ID,
            0,
            source,
            0
        )
        return device.injectEvent(event, Device.INJECT_MODE_ASYNC)
    }

    private fun injectChar(c: Char): Boolean {
        val decomposed = KeyComposition.decompose(c)
        val chars = decomposed?.toCharArray() ?: charArrayOf(c)
        val events = charMap?.getEvents(chars) ?: return false
        for (event in events) {
            if (!device.injectEvent(event, Device.INJECT_MODE_ASYNC)) {
                return false
            }
        }
        return true
    }

    private fun injectText(text: String): Int {
        var successCount = 0
        for (c in text.toCharArray()) {
            if (!injectChar(c)) {
                Ln.w("Could not inject char u+" + String.format("%04x", c.code))
                continue
            }
            successCount++
        }
        return successCount
    }

    private fun injectScroll(
        position: Position,
        hScroll: Float,
        vScroll: Float,
        buttons: Int
    ): Boolean {
        val now = SystemClock.uptimeMillis()
        val point = device.getPhysicalPoint(position)
            ?: // ignore event
            return false

        val props = pointerProperties[0]!!
        props.id = 0

        val coords = pointerCoords[0]!!
        coords.x = point.x.toFloat()
        coords.y = point.y.toFloat()
        coords.setAxisValue(MotionEvent.AXIS_HSCROLL, hScroll)
        coords.setAxisValue(MotionEvent.AXIS_VSCROLL, vScroll)

        val event = MotionEvent.obtain(
            lastTouchDown,
            now,
            MotionEvent.ACTION_SCROLL,
            1,
            pointerProperties,
            pointerCoords,
            0,
            buttons,
            1f,
            1f,
            DEFAULT_DEVICE_ID,
            0,
            InputDevice.SOURCE_MOUSE,
            0
        )
        return device.injectEvent(event, Device.INJECT_MODE_ASYNC)
    }

    fun processControlMsg(msg: ControlMsg) {
        val buffer = ByteBuffer.wrap(msg.data).order(ByteOrder.BIG_ENDIAN)

        when (msg.type) {
            ControlMsgType.INJECT_KEYCODE -> {
                val action = buffer.get()
                val keycode = buffer.int
                val repeat = buffer.int
                val metastate = buffer.int
                Ln.v("INJECT_KEYCODE: action=$action, keycode=$keycode, repeat=$repeat, metastate=$metastate")
                injectKeycode(action.toInt(), keycode, repeat, metastate)
            }

            ControlMsgType.INJECT_TOUCH_EVENT -> {
                val action = buffer.get()
                val pointId = buffer.long
                val x = buffer.int
                val y = buffer.int
                val w = buffer.short
                val h = buffer.short
                val pressure = buffer.float
                val actionButton = buffer.int
                val buttons = buffer.int
                Ln.v("INJECT_TOUCH_EVENT: action=$action,pointerId=$pointId, x=$x, y=$y, w=$w, h=$h, pressure=$pressure, actionButton=$actionButton, buttons=$buttons")
                val position = Position(x, y, w.toUInt().toInt(), h.toUInt().toInt())
                injectTouch(action.toInt(), pointId, position, pressure, actionButton, buttons)
            }

            ControlMsgType.INJECT_TEXT -> {
                val text = String(buffer.array())
                Ln.v("INJECT_TEXT: text=$text")
                injectText(text)
            }

            ControlMsgType.INJECT_SCROLL_EVENT -> {
                val x = buffer.int
                val y = buffer.int
                val w = buffer.short
                val h = buffer.short
                val hscroll = buffer.float
                val vscroll = buffer.float
                val buttons = buffer.int
                val position = Position(x, y, w.toUInt().toInt(), h.toUInt().toInt())
                Ln.v("INJECT_SCROLL_EVENT: x=$x, y=$y, w=$w, h=$h, hscroll=$hscroll, vscroll=$vscroll, buttons=$buttons")
                injectScroll(position, hscroll, vscroll, buttons)
            }

            else -> Ln.w("Unsupported message type: ${msg.type}")
        }
    }
}

@OptIn(ExperimentalStdlibApi::class)
fun main() {
    runBlocking {
        val selectorManager = SelectorManager(Dispatchers.IO)
        val socket = aSocket(selectorManager).tcp().connect("192.168.240.1", 10721)
//        val socket = aSocket(selectorManager).tcp().connect("127.0.0.1", 10721)

        val receiveChannel = socket.openReadChannel()
//        val sendChannel = socket.openWriteChannel(autoFlush = true)
        val options =
            Options.parse("1.0", "scid=12345678", "log_level=verbose", "audio=false", "video=false")
        Ln.initLogLevel(options.logLevel);
        val device = Device(options)
        val controller = Controller(device)

        launch(Dispatchers.IO) {
            while (true) {
                try {
                    val msg = receiveControlMsg(receiveChannel)
                    controller.processControlMsg(msg)
                } catch (e: Exception) {
                    Ln.e("Error receiving message: ${e.message}")
                    break
                }
            }
        }
    }

//        while (true) {
//            val myMessage = readln()
//            sendChannel.writeStringUtf8("$myMessage\n")
//        }
}

suspend fun receiveControlMsg(channel: ByteReadChannel): ControlMsg {
    val typeValue = channel.readByte()
    val type = ControlMsgType.entries.first { it.value == typeValue }

    val data = when (type) {
        ControlMsgType.INJECT_KEYCODE -> ByteArray(13).apply { channel.readFully(this) }
        ControlMsgType.INJECT_TOUCH_EVENT -> ByteArray(33).apply { channel.readFully(this) }
        ControlMsgType.INJECT_TEXT -> {
            val length = channel.readInt()
            ByteArray(length).apply {
                channel.readFully(this)
            }
        }

        ControlMsgType.INJECT_SCROLL_EVENT -> ByteArray(24).apply { channel.readFully(this) }
        else -> throw IllegalArgumentException("Unsupported message type: $type")
    }

    return ControlMsg(type, data)
}

//fun processControlMsg(msg: ControlMsg, device: Device) {
//    val buffer = ByteBuffer.wrap(msg.data).order(ByteOrder.BIG_ENDIAN)
//
//    when (msg.type) {
//        ControlMsgType.INJECT_KEYCODE -> {
//            val action = buffer.get()
//            val keycode = buffer.int
//            val repeat = buffer.int
//            val metastate = buffer.int
//            println("INJECT_KEYCODE: action=$action, keycode=$keycode, repeat=$repeat, metastate=$metastate")
//            device.injectKeyEvent(action.toInt(), keycode,repeat, metastate,  Device.INJECT_MODE_ASYNC)
//        }
//        ControlMsgType.INJECT_TOUCH_EVENT -> {
//            val action = buffer.get()
//            val x = buffer.int
//            val y = buffer.int
//            val w = buffer.short
//            val h = buffer.short
//            val pressure = buffer.float
//            val actionButton = buffer.int
//            val buttons = buffer.int
//            println("INJECT_TOUCH_EVENT: action=$action, x=$x, y=$y, w=$w, h=$h, pressure=$pressure,actionButton=$actionButton, buttons=$buttons")
//        }
//        ControlMsgType.INJECT_TEXT -> {
//            val text = String(buffer.array())
//            println("INJECT_TEXT: text=$text")
//        }
//        ControlMsgType.INJECT_SCROLL_EVENT -> {
//            val x = buffer.int
//            val y = buffer.int
//            val w = buffer.short
//            val h = buffer.short
//            val hscroll = buffer.float
//            val vscroll = buffer.float
//            val buttons = buffer.int
//            println("INJECT_SCROLL_EVENT: x=$x, y=$y, w=$w, h=$h, hscroll=$hscroll, vscroll=$vscroll, buttons=$buttons")
//        }
//        else -> println("Unsupported message type: ${msg.type}")
//    }
//}
