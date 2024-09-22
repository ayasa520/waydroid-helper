./gradlew assembleRelease
adb push app-release-unsigned.apk /data/local/tmp
adb shell CLASSPATH=/data/local/tmp/app-release-unsigned.apk app_process / com.rikka.simpleserver.MainKt 