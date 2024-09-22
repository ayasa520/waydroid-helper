#ifndef WAYLAND_MOUSE_LOCK_H
#define WAYLAND_MOUSE_LOCK_H

#include <wayland-client.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C"
{
#endif
    typedef struct
    {
        struct zwp_pointer_constraints_v1 *pointer_constraints;
        struct zwp_locked_pointer_v1 *locked_pointer;
        struct wl_seat *seat;
        struct wl_pointer *pointer;
        struct wl_compositor *compositor;
        struct wl_registry *wl_registry;
        struct zwp_relative_pointer_manager_v1 *relative_pointer_manager;
        struct zwp_relative_pointer_v1 *relative_pointer;
        struct wl_display *wl_display;
        struct wl_surface *wl_surface;
        // struct wl_event_queue *queue;
    } WaylandData;
    // 初始化 Wayland 鼠标锁定功能
    bool wayland_pointer_lock_init(struct wl_display *display, struct wl_surface *surface, void *data);

    // 锁定鼠标
    bool lock_pointer(void *data);

    // 解锁鼠标
    void unlock_pointer(void *data);

    void set_relative_motion_callback(void (*callback)(double, double, double, double));

    // 清理资源
    // void cleanup();

#ifdef __cplusplus
}
#endif

#endif // WAYLAND_MOUSE_LOCK_H