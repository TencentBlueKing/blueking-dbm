package osutil_test

import (
	"bytes"
	"encoding/json"
	"html/template"
	"testing"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
)

func TestIsFileExist(t *testing.T) {
	f := "/tmp/1.txt"
	d := "/tmp/asdad/"
	exist_f := osutil.FileExist(f)
	exist_d := osutil.FileExist(d)
	t.Log("f exist", exist_f)
	t.Log("d exist", exist_d)
}

func Test(t *testing.T) {
	type Person struct {
		Name string `json:"name"`
		Age  int    `json:"age"`
	}

	jsonData := `{"name": "John", "age": 30}`

	var p Person
	err := json.Unmarshal([]byte(jsonData), &p)
	if err != nil {
		panic(err)
	}

	t.Log(p.Name)
	t.Log(p.Age)

	conf := []byte(`{"name": "{{.Name}}", "age": {{.Age}}, "a":1}`)
	t.Log(string(conf))
	tmpl := template.Must(template.New("mytemplate").Parse(string(conf)))

	var rendered bytes.Buffer
	err = tmpl.Execute(&rendered, p)
	if err != nil {
		t.Log(err)
	}
	t.Log(rendered.String())
	var m map[string]interface{}
	_ = json.Unmarshal([]byte(rendered.String()), &m)
	t.Log(m)
	for key, value := range m {
		t.Log(key)
		t.Log(value)
	}

}
