module dbm-services/oracle/db-tools/dbactuator

go 1.26.0

require (
	github.com/cloudfoundry/gosigar v1.3.126
	github.com/dustin/go-humanize v1.0.1
	github.com/go-playground/validator/v10 v10.27.0
	github.com/godror/godror v0.40.4
	github.com/jaypipes/ghw v0.25.0
	github.com/pkg/errors v0.9.1
	github.com/shirou/gopsutil/v3 v3.24.5
	github.com/spf13/cobra v1.10.1
	golang.org/x/sys v0.47.0
)

require (
	github.com/go-logfmt/logfmt v0.6.0 // indirect
	github.com/godror/knownpb v0.1.2 // indirect
	google.golang.org/protobuf v1.36.12 // indirect
)

// 1.10.6是最后一个支持<v3.6的版本
replace go.mongodb.org/mongo-driver => go.mongodb.org/mongo-driver v1.10.6

require (
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/gabriel-vasile/mimetype v1.4.10 // indirect
	github.com/go-ole/go-ole v1.2.6 // indirect
	github.com/go-playground/locales v0.14.1 // indirect
	github.com/go-playground/universal-translator v0.18.1 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/jaypipes/pcidb v1.1.1 // indirect
	github.com/kr/pretty v0.3.1 // indirect
	github.com/leodido/go-urn v1.4.0 // indirect
	github.com/lufia/plan9stats v0.0.0-20211012122336-39d0f177ccd0 // indirect
	github.com/pmezard/go-difflib v1.0.1-0.20181226105442-5d4384ee4fb2 // indirect
	github.com/power-devops/perfstat v0.0.0-20210106213030-5aafc221ea8c // indirect
	github.com/spf13/pflag v1.0.10 // indirect
	github.com/stretchr/testify v1.11.1 // indirect
	github.com/tklauser/go-sysconf v0.3.12 // indirect
	github.com/tklauser/numcpus v0.6.1 // indirect
	github.com/yusufpapurcu/wmi v1.2.4 // indirect
	golang.org/x/crypto v0.55.0 // indirect
	golang.org/x/exp v0.0.0-20250620022241-b7579e27df2b // indirect
	golang.org/x/net v0.58.0 // indirect
	golang.org/x/text v0.41.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
	howett.net/plist v1.0.2-0.20250314012144-ee69052608d9 // indirect
)
