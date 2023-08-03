#!/bin/bash

# This script is used to reclaim the space of the qcow2 files.

# check if virt-sparsify is installed
[[ -z $(which virt-sparsify) ]] && echo "virt-sparsify is not installed" && exit 1

# usage
usage() {
    echo "Usage: $0 [-t <temp dir>] <qcow2 file>"
    exit 1
}

temp_dir="/tmp"
# use getopt to parse the command line options
while getopts ":t:" o; do
    case "${o}" in
        t)
            temp_dir=${OPTARG}
            [[ ! -d $temp_dir ]] && echo "$temp_dir is not a directory" && exit 1
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

# get qcow2 file path from command line
qcow2_file=$1
[[ ! -f $qcow2_file ]] && echo "$qcow2_file is not a file" && exit 1o

# print the qcow2 file path and the temp dir path
echo "qcow2 file: $qcow2_file"
echo "temp dir: $temp_dir"

# use virt-sparsify to reclaim the space of the qcow2 file
echo "virt-sparsify --tmp $temp_dir $qcow2_file temp.$qcow2_file"
flock -x -w1 $qcow2_file virt-sparsify --tmp $temp_dir $qcow2_file $temp_dir/temp.$qcow2_file || exit 1
mv $temp_dir/temp.$qcow2_file $qcow2_file || exit 1
