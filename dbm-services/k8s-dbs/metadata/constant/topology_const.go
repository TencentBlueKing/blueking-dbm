package constant

// RelationType 定义 relation 类型结构体
type RelationType struct {
	TypeName  string `json:"typeName"`
	TypeAlias string `json:"typeAlias"`
}

// RelationType 关系具体类型
var (
	Read      = RelationType{"read", "读取"}
	Write     = RelationType{"write", "写入"}
	ReadWrite = RelationType{"read-write", "读写"}
	Bind      = RelationType{TypeName: "bind", TypeAlias: "绑定"}
	Sync      = RelationType{TypeName: "sync", TypeAlias: "同步"}
	Entry     = RelationType{TypeName: "entry", TypeAlias: "访问"}
)

// RelationDirection 定义关系边方向
type RelationDirection string

// 关系边方向类型
const (
	Single RelationDirection = "single"
	Multi  RelationDirection = "multi"
	None   RelationDirection = "none"
)
