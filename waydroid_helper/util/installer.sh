#!/bin/bash

cd $startdir
source ./EXTENSION


# call pre_install
call_pre_install(){
    rm -rf $srcdir && mkdir -p $srcdir
    rm -rf $pkgdir && mkdir -p $pkgdir
    pre_install
}

call_post_install(){
    if type post_install 2>/dev/null | grep -q 'function'; then
        post_install
    fi
}