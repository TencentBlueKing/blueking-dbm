#!/bin/bash

mkdir -p /tmp/dbha

# install abseil
cd /tmp/dbha

wget https://github.com/abseil/abseil-cpp/archive/refs/tags/20250127.1.tar.gz --no-check-certificate
tar -xzvf 20250127.1.tar.gz
cd abseil-cpp-20250127.1
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF \
  -DABSL_BUILD_TESTING=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DABSL_ENABLE_INSTALL=ON \
  -DCMAKE_INSTALL_PREFIX=/usr/local/abseil/20250127.1

cmake --build . -j --target all
cmake --install .

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF \
  -DABSL_BUILD_TESTING=OFF \
  -DBUILD_SHARED_LIBS=ON \
  -DABSL_ENABLE_INSTALL=ON \
  -DCMAKE_INSTALL_PREFIX=/usr/local/abseil/20250127.1

cmake --build . -j --target all
cmake --install .


# install protobuff
cd /tmp/dbha

wget https://github.com/protocolbuffers/protobuf/releases/download/v30.2/protobuf-30.2.tar.gz --no-check-certificate
tar -vxf protobuf-30.2.tar.gz
cd protobuf-30.2/
mkdir build
cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr/local/protobuf-30.2 \
  -Dprotobuf_BUILD_TESTS=OFF \
  -Dprotobuf_BUILD_EXAMPLES=OFF \
  -Dprotobuf_BUILD_SHARED_LIBS=ON

cmake --build . -j
cmake --install .

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr/local/protobuf-30.2 \
  -Dprotobuf_BUILD_TESTS=OFF \
  -Dprotobuf_BUILD_EXAMPLES=OFF \
  -Dprotobuf_BUILD_SHARED_LIBS=OFF

cmake --build . -j
cmake --install .

cd /tmp
rm -rf /tmp/dbha

# install grpc tools
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
