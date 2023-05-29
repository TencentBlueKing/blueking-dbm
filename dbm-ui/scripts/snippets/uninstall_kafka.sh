#!/bin/bash

supervisorctl stop kafka
supervisorctl stop zookeeper
rm -rf /data/kafkadata