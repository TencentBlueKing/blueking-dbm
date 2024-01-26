module dbm-services/mongo/db-tools/dbactuator

go 1.18

require (
	github.com/dustin/go-humanize v1.0.0
	github.com/go-playground/validator/v10 v10.11.0
	github.com/pkg/errors v0.9.1
	github.com/spf13/cobra v1.7.0
	go.mongodb.org/mongo-driver v1.10.6
	golang.org/x/sys v0.11.0
	gopkg.in/yaml.v2 v2.4.0
)

// 1.10.6是最后一个支持<v3.6的版本
replace go.mongodb.org/mongo-driver => go.mongodb.org/mongo-driver v1.10.6

require (
	github.com/go-playground/locales v0.14.0 // indirect
	github.com/go-playground/universal-translator v0.18.0 // indirect
	github.com/golang/snappy v0.0.1 // indirect
	github.com/google/go-cmp v0.5.9 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/klauspost/compress v1.13.6 // indirect
	github.com/leodido/go-urn v1.2.1 // indirect
	github.com/montanaflynn/stats v0.0.0-20171201202039-1bf9dbcd8cbe // indirect
	github.com/spf13/pflag v1.0.5 // indirect
	github.com/stretchr/testify v1.8.1 // indirect
	github.com/xdg-go/pbkdf2 v1.0.0 // indirect
	github.com/xdg-go/scram v1.1.2 // indirect
	github.com/xdg-go/stringprep v1.0.4 // indirect
	github.com/youmark/pkcs8 v0.0.0-20181117223130-1be2e3e5546d // indirect
	golang.org/x/crypto v0.0.0-20220622213112-05595931fe9d // indirect
	golang.org/x/sync v0.0.0-20220722155255-886fb9371eb4 // indirect
	golang.org/x/text v0.7.0 // indirect
)
