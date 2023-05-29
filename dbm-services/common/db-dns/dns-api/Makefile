SRV_NAME = bk-dnsapi
VER = v0.2.0
CURRENT_VERSION = release-$(VER)
NAMESPACE = sccmsp
DH_URL = mirrors.tencent.com

hook:
	cp ./scripts/git/pre-commit ./.git/hooks/pre-commit && chmod 711 ./.git/hooks/pre-commit

clean:
	-rm ./$(SRV_NAME)

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o $(SRV_NAME) -v ./cmd/$(SRV_NAME)

publish:build
	docker build --build-arg SRV_NAME=$(SRV_NAME) --rm -t $(SRV_NAME):$(CURRENT_VERSION) .
	docker tag $(SRV_NAME):$(CURRENT_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)

.PHONY: init clean build publish gotool clean help api curl
