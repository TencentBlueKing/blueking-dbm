module k8s-dbs

go 1.24.2

require (
	github.com/apecloud/kbcli v0.9.3
	github.com/apecloud/kubeblocks v1.0.0
	github.com/gin-gonic/gin v1.10.0
	github.com/go-playground/validator/v10 v10.25.0
	github.com/go-resty/resty/v2 v2.16.5
	github.com/google/go-cmp v0.7.0
	github.com/google/uuid v1.6.0
	github.com/imdario/mergo v0.3.16
	github.com/jinzhu/copier v0.4.0
	github.com/mitchellh/mapstructure v1.5.1-0.20220423185008-bf980b35cac4
	github.com/pkg/errors v0.9.1
	github.com/samber/lo v1.51.0
	github.com/stretchr/testify v1.10.0
	github.com/testcontainers/testcontainers-go v0.38.0
	github.com/testcontainers/testcontainers-go/modules/mysql v0.38.0
	go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin v0.60.0
	golang.org/x/text v0.27.0
	gorm.io/driver/mysql v1.5.7
	gorm.io/gorm v1.25.12
	helm.sh/helm/v3 v3.18.5
	k8s.io/api v0.33.3
	k8s.io/apimachinery v0.33.3
	k8s.io/cli-runtime v0.33.3
	k8s.io/client-go v12.0.0+incompatible
	k8s.io/metrics v0.33.2
	k8s.io/utils v0.0.0-20241104100929-3ea5e8cea738
	sigs.k8s.io/yaml v1.5.0
)

require (
	dario.cat/mergo v1.0.1 // indirect
	github.com/Azure/go-ansiterm v0.0.0-20250102033503-faa5f7b0171c // indirect
	github.com/BurntSushi/toml v1.5.0 // indirect
	github.com/MakeNowJust/heredoc v1.0.0 // indirect
	github.com/Masterminds/goutils v1.1.1 // indirect
	github.com/Masterminds/semver/v3 v3.3.0 // indirect
	github.com/Masterminds/sprig/v3 v3.3.0 // indirect
	github.com/Masterminds/squirrel v1.5.4 // indirect
	github.com/Microsoft/go-winio v0.6.2 // indirect
	github.com/asaskevich/govalidator v0.0.0-20230301143203-a9d515a09cc2 // indirect
	github.com/beorn7/perks v1.0.1 // indirect
	github.com/blang/semver/v4 v4.0.0 // indirect
	github.com/bytedance/sonic v1.12.10 // indirect
	github.com/bytedance/sonic/loader v0.2.3 // indirect
	github.com/cenkalti/backoff/v4 v4.3.0 // indirect
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/chai2010/gettext-go v1.0.2 // indirect
	github.com/cloudwego/base64x v0.1.5 // indirect
	github.com/containerd/containerd v1.7.27 // indirect
	github.com/containerd/errdefs v1.0.0 // indirect
	github.com/containerd/errdefs/pkg v0.3.0 // indirect
	github.com/containerd/log v0.1.0 // indirect
	github.com/containerd/platforms v0.2.1 // indirect
	github.com/cpuguy83/dockercfg v0.3.2 // indirect
	github.com/cyphar/filepath-securejoin v0.4.1 // indirect
	github.com/davecgh/go-spew v1.1.2-0.20180830191138-d8f796af33cc // indirect
	github.com/distribution/reference v0.6.0 // indirect
	github.com/docker/docker v28.3.3+incompatible // indirect
	github.com/docker/go-connections v0.5.0 // indirect
	github.com/docker/go-units v0.5.0 // indirect
	github.com/ebitengine/purego v0.8.4 // indirect
	github.com/emicklei/go-restful/v3 v3.11.0 // indirect
	github.com/evanphx/json-patch v5.9.11+incompatible // indirect
	github.com/evanphx/json-patch/v5 v5.9.0 // indirect
	github.com/exponent-io/jsonpath v0.0.0-20210407135951-1de76d718b3f // indirect
	github.com/fatih/color v1.16.0 // indirect
	github.com/felixge/httpsnoop v1.0.4 // indirect
	github.com/fsnotify/fsnotify v1.7.0 // indirect
	github.com/gabriel-vasile/mimetype v1.4.8 // indirect
	github.com/gin-contrib/sse v1.0.0 // indirect
	github.com/go-errors/errors v1.4.2 // indirect
	github.com/go-gorp/gorp/v3 v3.1.0 // indirect
	github.com/go-logr/logr v1.4.2 // indirect
	github.com/go-logr/stdr v1.2.2 // indirect
	github.com/go-ole/go-ole v1.3.0 // indirect
	github.com/go-openapi/jsonpointer v0.21.0 // indirect
	github.com/go-openapi/jsonreference v0.21.0 // indirect
	github.com/go-openapi/swag v0.23.0 // indirect
	github.com/go-playground/locales v0.14.1 // indirect
	github.com/go-playground/universal-translator v0.18.1 // indirect
	github.com/go-sql-driver/mysql v1.8.1 // indirect
	github.com/gobwas/glob v0.2.3 // indirect
	github.com/goccy/go-json v0.10.5 // indirect
	github.com/gogo/protobuf v1.3.2 // indirect
	github.com/golang/groupcache v0.0.0-20210331224755-41bb18bfe9da // indirect
	github.com/golang/protobuf v1.5.4 // indirect
	github.com/google/btree v1.1.3 // indirect
	github.com/google/gnostic-models v0.6.9 // indirect
	github.com/google/gofuzz v1.2.0 // indirect
	github.com/google/shlex v0.0.0-20191202100458-e7afc7fbc510 // indirect
	github.com/gorilla/websocket v1.5.4-0.20250319132907-e064f32e3674 // indirect
	github.com/gosuri/uitable v0.0.4 // indirect
	github.com/gregjones/httpcache v0.0.0-20190611155906-901d90724c79 // indirect
	github.com/hashicorp/errwrap v1.1.0 // indirect
	github.com/hashicorp/go-multierror v1.1.1 // indirect
	github.com/hashicorp/hcl v1.0.1-vault-5 // indirect
	github.com/huandu/xstrings v1.5.0 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/jmoiron/sqlx v1.4.0 // indirect
	github.com/josharian/intern v1.0.0 // indirect
	github.com/json-iterator/go v1.1.12 // indirect
	github.com/klauspost/compress v1.18.0 // indirect
	github.com/klauspost/cpuid/v2 v2.2.10 // indirect
	github.com/lann/builder v0.0.0-20180802200727-47ae307949d0 // indirect
	github.com/lann/ps v0.0.0-20150810152359-62de8c46ede0 // indirect
	github.com/leodido/go-urn v1.4.0 // indirect
	github.com/lib/pq v1.10.9 // indirect
	github.com/liggitt/tabwriter v0.0.0-20181228230101-89fcab3d43de // indirect
	github.com/lufia/plan9stats v0.0.0-20211012122336-39d0f177ccd0 // indirect
	github.com/magiconair/properties v1.8.10 // indirect
	github.com/mailru/easyjson v0.9.0 // indirect
	github.com/mattn/go-colorable v0.1.13 // indirect
	github.com/mattn/go-isatty v0.0.20 // indirect
	github.com/mattn/go-runewidth v0.0.16 // indirect
	github.com/mitchellh/copystructure v1.2.0 // indirect
	github.com/mitchellh/go-wordwrap v1.0.1 // indirect
	github.com/mitchellh/reflectwalk v1.0.2 // indirect
	github.com/moby/docker-image-spec v1.3.1 // indirect
	github.com/moby/go-archive v0.1.0 // indirect
	github.com/moby/patternmatcher v0.6.0 // indirect
	github.com/moby/spdystream v0.5.0 // indirect
	github.com/moby/sys/sequential v0.6.0 // indirect
	github.com/moby/sys/user v0.4.0 // indirect
	github.com/moby/sys/userns v0.1.0 // indirect
	github.com/moby/term v0.5.2 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	github.com/monochromegane/go-gitignore v0.0.0-20200626010858-205db1a8cc00 // indirect
	github.com/morikuni/aec v1.0.0 // indirect
	github.com/munnerz/goautoneg v0.0.0-20191010083416-a7dc8b61c822 // indirect
	github.com/mxk/go-flowrate v0.0.0-20140419014527-cca7078d478f // indirect
	github.com/opencontainers/go-digest v1.0.0 // indirect
	github.com/opencontainers/image-spec v1.1.1 // indirect
	github.com/pelletier/go-toml/v2 v2.2.3 // indirect
	github.com/peterbourgon/diskv v2.0.1+incompatible // indirect
	github.com/pmezard/go-difflib v1.0.1-0.20181226105442-5d4384ee4fb2 // indirect
	github.com/power-devops/perfstat v0.0.0-20210106213030-5aafc221ea8c // indirect
	github.com/prometheus/client_golang v1.22.0 // indirect
	github.com/prometheus/client_model v0.6.1 // indirect
	github.com/prometheus/common v0.62.0 // indirect
	github.com/prometheus/procfs v0.15.1 // indirect
	github.com/rivo/uniseg v0.4.7 // indirect
	github.com/rubenv/sql-migrate v1.8.0 // indirect
	github.com/russross/blackfriday/v2 v2.1.0 // indirect
	github.com/sagikazarmark/locafero v0.4.0 // indirect
	github.com/sagikazarmark/slog-shim v0.1.0 // indirect
	github.com/santhosh-tekuri/jsonschema/v6 v6.0.2 // indirect
	github.com/shirou/gopsutil/v4 v4.25.5 // indirect
	github.com/shopspring/decimal v1.4.0 // indirect
	github.com/sirupsen/logrus v1.9.3 // indirect
	github.com/sourcegraph/conc v0.3.0 // indirect
	github.com/spf13/afero v1.11.0 // indirect
	github.com/spf13/cast v1.7.0 // indirect
	github.com/spf13/cobra v1.9.1 // indirect
	github.com/spf13/pflag v1.0.7 // indirect
	github.com/spf13/viper v1.19.0 // indirect
	github.com/subosito/gotenv v1.6.0 // indirect
	github.com/tklauser/go-sysconf v0.3.12 // indirect
	github.com/tklauser/numcpus v0.6.1 // indirect
	github.com/twitchyliquid64/golang-asm v0.15.1 // indirect
	github.com/ugorji/go/codec v1.2.12 // indirect
	github.com/xlab/treeprint v1.2.0 // indirect
	github.com/yusufpapurcu/wmi v1.2.4 // indirect
	go.opentelemetry.io/auto/sdk v1.1.0 // indirect
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.58.0 // indirect
	go.opentelemetry.io/otel v1.35.0 // indirect
	go.opentelemetry.io/otel/metric v1.35.0 // indirect
	go.opentelemetry.io/otel/trace v1.35.0 // indirect
	go.uber.org/multierr v1.11.0 // indirect
	go.yaml.in/yaml/v2 v2.4.2 // indirect
	go.yaml.in/yaml/v3 v3.0.3 // indirect
	golang.org/x/arch v0.14.0 // indirect
	golang.org/x/crypto v0.40.0 // indirect
	golang.org/x/exp v0.0.0-20240719175910-8a7402abbf56 // indirect
	golang.org/x/net v0.41.0 // indirect
	golang.org/x/oauth2 v0.28.0 // indirect
	golang.org/x/sync v0.16.0 // indirect
	golang.org/x/sys v0.34.0 // indirect
	golang.org/x/term v0.33.0 // indirect
	golang.org/x/time v0.9.0 // indirect
	gomodules.xyz/jsonpatch/v2 v2.4.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20241209162323-e6fa225c2576 // indirect
	google.golang.org/grpc v1.68.1 // indirect
	google.golang.org/protobuf v1.36.5 // indirect
	gopkg.in/evanphx/json-patch.v4 v4.12.0 // indirect
	gopkg.in/inf.v0 v0.9.1 // indirect
	gopkg.in/ini.v1 v1.67.0 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
	k8s.io/apiextensions-apiserver v0.33.3 // indirect
	k8s.io/apiserver v0.33.3 // indirect
	k8s.io/component-base v0.33.3 // indirect
	k8s.io/klog/v2 v2.130.1 // indirect
	k8s.io/kube-openapi v0.0.0-20250318190949-c8a335a9a2ff // indirect
	k8s.io/kubectl v0.33.3 // indirect
	oras.land/oras-go/v2 v2.6.0 // indirect
	sigs.k8s.io/controller-runtime v0.17.2 // indirect
	sigs.k8s.io/json v0.0.0-20241010143419-9aa6b5e7a4b3 // indirect
	sigs.k8s.io/kustomize/api v0.19.0 // indirect
	sigs.k8s.io/kustomize/kyaml v0.19.0 // indirect
	sigs.k8s.io/randfill v1.0.0 // indirect
	sigs.k8s.io/structured-merge-diff/v4 v4.6.0 // indirect
)

replace (
	github.com/docker/cli => github.com/docker/cli v24.0.7+incompatible
	github.com/docker/distribution => github.com/docker/distribution v2.8.2+incompatible
	//github.com/docker/docker => github.com/moby/moby v26.0.0+incompatible
	github.com/spf13/afero => github.com/spf13/afero v1.2.2
)

replace (
	github.com/go-sql-driver/mysql => github.com/go-sql-driver/mysql v1.7.1
	// golang.org/x/exp => golang.org/x/exp v0.0.0-20230711153332-06a737ee72cb
	k8s.io/api => k8s.io/api v0.29.2
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.29.2
	k8s.io/apimachinery => k8s.io/apimachinery v0.29.2
	k8s.io/apiserver => k8s.io/apiserver v0.29.2
	k8s.io/cli-runtime => k8s.io/cli-runtime v0.29.2
	k8s.io/client-go => k8s.io/client-go v0.29.2
	k8s.io/cloud-provider => k8s.io/cloud-provider v0.29.2
	k8s.io/cluster-bootstrap => k8s.io/cluster-bootstrap v0.29.2
	k8s.io/code-generator => k8s.io/code-generator v0.29.2
	k8s.io/component-base => k8s.io/component-base v0.29.2
	k8s.io/component-helpers => k8s.io/component-helpers v0.29.2
	k8s.io/controller-manager => k8s.io/controller-manager v0.29.2
	k8s.io/cri-api => k8s.io/cri-api v0.29.2
	k8s.io/csi-translation-lib => k8s.io/csi-translation-lib v0.29.2
	k8s.io/dynamic-resource-allocation => k8s.io/dynamic-resource-allocation v0.29.2
	k8s.io/endpointslice => k8s.io/endpointslice v0.29.2
	k8s.io/kms => k8s.io/kms v0.29.2
	k8s.io/kube-aggregator => k8s.io/kube-aggregator v0.29.2
	k8s.io/kube-controller-manager => k8s.io/kube-controller-manager v0.29.2
	k8s.io/kube-proxy => k8s.io/kube-proxy v0.29.2
	k8s.io/kube-scheduler => k8s.io/kube-scheduler v0.29.2
	k8s.io/kubectl => k8s.io/kubectl v0.29.2
	k8s.io/kubelet => k8s.io/kubelet v0.29.2
	k8s.io/kubernetes/staging/src/k8s.io/apimachinery => k8s.io/apimachinery v0.0.0-20250611063655-8052df02af25
	k8s.io/legacy-cloud-providers => k8s.io/legacy-cloud-providers v0.29.2
	k8s.io/metrics => k8s.io/metrics v0.29.2
	k8s.io/mount-utils => k8s.io/mount-utils v0.29.2
	k8s.io/pod-security-admission => k8s.io/pod-security-admission v0.29.2
	k8s.io/sample-apiserver => k8s.io/sample-apiserver v0.29.2
	k8s.io/sample-cli-plugin => k8s.io/sample-cli-plugin v0.29.2
	k8s.io/sample-controller => k8s.io/sample-controller v0.29.2
)
