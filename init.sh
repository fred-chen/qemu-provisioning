#!/bin/bash

usage() {
    printf "\nUsage: $(basename $0) <cloud_image_dir>\n\n"
    exit 1
}

init_ubuntu() {
    apt-get update
    apt-get -y install python3-pip
    apt-get install cloud-image-utils
    pip3 install PyYaml
}

main () {
    CLOUD_IMG_DIR=$1
    [[ -z ${CLOUD_IMG_DIR} ]] && usage
    [[ -d ${CLOUD_IMG_DIR} ]] || { 
            echo "${CLOUD_IMG_DIR} does not exist! Making one..."; 
            mkdir -p ${CLOUD_IMG_DIR}; 
        }
    echo "cloud-image-dir: ${CLOUD_IMG_DIR}" > settings.yaml
    source /etc/os-release && echo "OS: $NAME"

    case $NAME in
        "Ubuntu") init_ubuntu
            ;;
        *) echo "Unsupported OS Distribution"
            ;;
    esac
}

main $@