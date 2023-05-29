#!/bin/bash

workDir=`pwd`

# unit test
cd  $workDir
chmod +x *.sh
./build_doc.sh
make