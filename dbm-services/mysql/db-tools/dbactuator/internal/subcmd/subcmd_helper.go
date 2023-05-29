package subcmd

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/docs"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

const (
	// DTString TODO
	DTString = "string"
	// DTInteger TODO
	DTInteger = "integer"
	// DTNumber TODO
	DTNumber = "number"
	// DTObject TODO
	DTObject = "object"
	// DTArray TODO
	DTArray = "array"
	// DTArrayObject TODO
	DTArrayObject = "array object"
	// DTBOOLEAN TODO
	DTBOOLEAN = "boolean"
	// DTUndefined TODO
	DTUndefined = "undefined ref"
	// RefMaxDepth TODO
	RefMaxDepth = 9
)

const (
	// DefinitionPrefix TODO
	DefinitionPrefix = "#/definitions/"
	// RefKey TODO
	RefKey = "$ref"
	// IndentStep TODO
	IndentStep = "    "
	// DefinitionKey TODO
	DefinitionKey = "post"
)

// PostPath TODO
type PostPath map[string]*Path // "post": {}
// Path TODO
type Path struct {
	Description string           `json:"description"`
	Summary     string           `json:"summary"`
	Parameters  []Param          `json:"parameters"` // parameters[0].schema.$ref
	Responses   map[string]Param `json:"responses"`
}

// PrintDescription TODO
func (p *Path) PrintDescription() {
	fmt.Printf("# Summary: %s\n", p.Summary)
	if p.Description != "" {
		fmt.Printf("# Description: %s\n", p.Description)
	}
}

// Param TODO
type Param struct {
	Schema      RefMap `json:"schema"` // {"$ref":""}
	Name        string `json:"name"`
	Description string `json:"description"`
}

// RefMap TODO
type RefMap map[string]string // "$ref":"#/definitions/xx"

// RefMapObj TODO
type RefMapObj struct {
	Ref string `json:"$ref"`
}

// Parameter TODO
type Parameter struct {
	Type string `json:"type"`
	// Properties   components.BaseInputParam `json:"properties"`
	GeneralParam components.GeneralParam `json:"generalParam"` // generalParam.$ref
	Params       Definition              `json:"params"`       // params.$ref
}

// Definition TODO
type Definition struct {
	Type        string               `json:"type"`
	Required    []string             `json:"required"`
	Properties  map[string]*Property `json:"properties"`
	description string
	depth       int // 禁止无限套娃
	name        string
	expanded    bool
}

// PrintProperties TODO
func (d *Definition) PrintProperties(indent string, header string) {
	if indent == "" {
		fmt.Printf("%s: %s\n", header, d.description)
	}
	indent = IndentStep + indent
	for _, prop := range d.Properties {
		prop.Print(indent)
	}
}

// NestedRef TODO
type NestedRef struct {
	Type string `json:"type"`
	RefMapObj
	Items *NestedRef `json:"items"`
}

// Property TODO
type Property struct {
	Type                 string        `json:"type"`
	Description          string        `json:"description"`
	Example              interface{}   `json:"example"`
	Default              interface{}   `json:"default"`
	Enum                 []interface{} `json:"enum"`
	AdditionalProperties *NestedRef    `json:"additionalProperties"` // additionalProperties.$ref
	Ref                  string        `json:"$ref"`                 // $ref, RefKey
	Items                *NestedRef    `json:"items"`                // array: items.$ref

	additionalProperties map[string]*Definition
	ref                  *Definition
	required             bool
	name                 string
	depth                int // 禁止无限套娃
}

func wrapperBoolean(flag bool) string {
	if flag {
		return " Required,"
	} else {
		return " " // Optional
	}
}

func wrapperType(t string) string {
	if t == DTObject {
		return "dict"
	} else if t == DTNumber {
		return "float"
	}
	return t
}

func wrapperEnum(v []interface{}) string {
	var enumStr = ""
	if v != nil && len(v) > 0 {
		enumStr = fmt.Sprintf(` Enum oneof%v,`, v)
	}
	return enumStr
}

// Print TODO
func (p *Property) Print(indent string) {
	leftMaxPad := "20"
	left := fmt.Sprintf("%s%s:", indent, p.name)

	leftWithPad := fmt.Sprintf("%-"+leftMaxPad+"s", left)
	ss := fmt.Sprintf(
		"%s\t%s,%s%s %s",
		leftWithPad, p.Type, wrapperBoolean(p.required), wrapperEnum(p.Enum), p.Description,
	)
	if p.Example != nil {
		ss += fmt.Sprintf(". 例: %v", p.Example)
	}
	if p.Default != nil {
		ss += fmt.Sprintf(", 默认值: %v", p.Default)
	}
	if p.ref != nil {
		fmt.Println(ss)
		p.ref.PrintProperties(indent, p.ref.description)
	} else {
		fmt.Println(ss)
	}
}

// Definitions TODO
type Definitions map[string]*Definition

// JsonSpec TODO
type JsonSpec struct {
	Paths       map[string]PostPath `json:"paths"`
	Definitions Definitions         `json:"definitions"`
}

// GetOneDefinition TODO
func (ds *Definitions) GetOneDefinition(name string) *Definition {
	name = strings.TrimPrefix(name, DefinitionPrefix)
	if obj, ok := (*ds)[name]; ok {
		return obj
	} else {
		// 未定义的 definition name
	}
	return nil
}

// expandProperties 将 ref definition 展开
func (ds *Definitions) expandProperties() {
	for defName, d := range *ds {
		d.name = defName
		if !d.expanded { // 因为展开时，一直在操作同一个引用，不要重复展开
			d.ExpandProperties(ds)
		}
	}
}

// ExpandProperties 展开 definition 的 property
// 因为 property 可能引用其它 definition
func (d *Definition) ExpandProperties(defs *Definitions) {
	d.expanded = true
	if d.Type != DTObject {
		logger.Info("helper definition is no object %v", d)
		return
	}
	for pname, prop := range d.Properties {
		prop.depth = d.depth
		prop.name = pname
		if util.ContainElem(d.Required, pname) {
			prop.required = true
		}

		refObjName := prop.getRef()
		if refObjName != "" {
			prop.ref = defs.GetOneDefinition(refObjName)
			if prop.ref == nil {
				prop.Type = DTUndefined // 未知 definition, 置空
				prop.Ref = ""
				continue
			}
			prop.ref.depth = prop.depth + 1
			d.depth = prop.ref.depth
			if d.depth > RefMaxDepth {
				fmt.Printf(
					"ref max depth exceed, definition name:%v, depth:%d, depth def:%v\n",
					d.name, d.depth, prop.ref,
				)
				continue
			}
			prop.ref.ExpandProperties(defs) // 递归
			prop.ref.description = prop.Description
			if prop.Type == "" {
				prop.Type = DTObject
			}
		}
	}
}

// getRef 判断该 property 是否有下级嵌套
// 如果有则存到 ref 中，且修改 Type 加上 嵌套类型
func (p *Property) getRef() string {
	if p.Ref != "" {
		p.Type += " " + DTObject
		return p.Ref
	} else if p.AdditionalProperties != nil {
		p.Type += ":map[string]" + " " + p.AdditionalProperties.Type // DTString
		return p.getItemsNestedRef(p.AdditionalProperties)
	} else if p.Items != nil {
		p.Type += " " + p.Items.Type
		return p.getItemsNestedRef(p.Items)
	}
	return ""
}

func (p *Property) getItemsNestedRef(subRef *NestedRef) string {
	if ref := subRef.RefMapObj.Ref; ref != "" {
		p.Ref = ref
		p.Type += " " + DTObject // DTArrayObject
		return ref
	} else if subRef.Items != nil {
		if ref = subRef.Items.RefMapObj.Ref; ref != "" {
			p.Ref = ref
			p.Type += " " + DTObject // DTArrayObject
			return ref
		}
		p.Type += " " + subRef.Items.Type
	}
	return ""
}

// GetPathDefinitionHelper 结束命令字符串，打印描述
// mysql mycnf-change
// /mysql/mycnf-change
func GetPathDefinitionHelper(subcmd string) error {
	defer func() {
		if r := recover(); r != nil {
			// logger.Error("get helper failed %s: %s", subcmd, r, string(debug.Stack()))
		}
	}()
	if strings.Contains(subcmd, " ") {
		tmp := strings.Split(strings.TrimSpace(subcmd), " ")
		subcmd = "/" + strings.Join(tmp, "/")
	}
	f := docs.SwaggerDocs
	doc := "swagger.json"
	b, err := f.ReadFile(doc)
	if err != nil {
		return err
	}
	jsonSpec := JsonSpec{}
	if err := json.Unmarshal(b, &jsonSpec); err != nil {
		fmt.Println(err)
		log.Fatalln("docs/swagger.json 解析失败")
	}
	if pathObj, ok := jsonSpec.Paths[subcmd]; !ok {
		fmt.Printf("未找到参数定义 %s\n", subcmd)
	} else {
		if params, ok := pathObj[DefinitionKey]; !ok {
			fmt.Printf("未找到参数定义post %s\n", subcmd)
		} else if len(params.Parameters) == 0 {
			fmt.Printf("未找到参数定义param %s\n", subcmd)
		}
	}
	// jsonSpec.Definitions.ExpandProperties()
	pathDefinition := jsonSpec.Paths[subcmd][DefinitionKey]
	pathDefinition.PrintDescription()
	// parameters
	reqSchema := pathDefinition.Parameters[0].Schema
	schemaName := strings.TrimPrefix(reqSchema[RefKey], DefinitionPrefix)
	thisDef := jsonSpec.Definitions[schemaName]
	thisDef.ExpandProperties(&jsonSpec.Definitions)
	thisDef.PrintProperties("", "\n# Param")

	// responses
	for code, resp := range pathDefinition.Responses {
		respSchema := resp.Schema
		schemaName = strings.TrimPrefix(respSchema[RefKey], DefinitionPrefix)
		thisDef = jsonSpec.Definitions[schemaName]
		thisDef.ExpandProperties(&jsonSpec.Definitions) // 如果 param 对象里面包含了 resp 的对象，这里可能重复展开。暂不处理
		thisDef.PrintProperties("", "\n# Response "+code)
	}
	return nil
}
