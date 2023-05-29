1. 命令行启动看 help
2. 容器启动 docker run -d --name test-parser -p 22222:22222 -e SQ_ADDRESS=0.0.0.0:22222 -e SQ_TMYSQLPARSER_BIN=/tmysqlparse ${THIS_IMAGE}