#!/bin/bash


function CheckHex {
    #file path, Ghidra offset, Hex to check
    commandoutput="$(od $1 --skip-bytes=$(($2-0x100000)) --read-bytes=$((${#3} / 2)) --endian=little -t x1 -An file | sed 's/ //g')"
    if [ "$commandoutput" = "$3" ]; then
        echo "1"
    else
        echo "0"
    fi
}

function PatchHex {
    #file path, ghidra offset, original hex, new hex
    file_offset=$(($2-0x100000))
    if [ $(CheckHex $1 $2 $3) = "1" ]; then
        hexinbin=$(printf $4 | xxd -r -p)
        echo -n $hexinbin | dd of=$1 seek=$file_offset bs=1 conv=notrunc;
        tmp="Patched $1 at $file_offset with new hex $4"
        echo $tmp
        elif [ $(CheckHex $1 $2 $4) = "1" ]; then
        echo "Already patched"
    else
        echo "Hex mismatch!"
    fi
}

houdini_path="/var/lib/waydroid/overlay/system/lib64/libhoudini.so"

if [ -f $houdini_path ]; then
    if [ -w houdini_path ] || [ "$EUID" = 0 ]; then
        PatchHex $houdini_path 0x4062a5 48b8fbffffff 48b8ffffffff
        PatchHex $houdini_path 0x4099d6 83e0fb 83e0ff
        PatchHex $houdini_path 0x409b42 e8892feeff 9090909090
    else
        echo "Libhoudini is not writeable. Please run with sudo"
    fi
else
    echo "Libhoudini not found. Please install it first."
fi








