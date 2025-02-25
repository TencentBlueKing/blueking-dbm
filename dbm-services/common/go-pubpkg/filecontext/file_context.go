package filecontext

import (
	"bytes"
	"encoding/gob"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/gofrs/flock"
	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gopkg.in/yaml.v2"
)

func main() {
	/*
		fc := NewFileContext("test.ctx.json")
		fc.Set("test", "test", false)
		fc.Set("test", "test1111", false)
		fc.Set("test3", 1, false)
		fmt.Println(fc.Set("test2", "test2", true))

		fmt.Println(fc.Get("test"))
	*/

	/*
		fc := NewFileContext("test.ctx.gob")
		fmt.Println(fc.Get("test"))
		fmt.Println(fc.Get("test222"))
		fc.Set("test222", "test222", true)
		fmt.Println(fc.Get("test222"))

	*/
	fc := NewFileContext("test.ctx.gob")
	fmt.Println(fc.Get("test222", false))
}

// FileContext is a struct that stores data in a file.
// file suffix is .ctx.gob or .ctx.json
type FileContext struct {
	contextFile string
	format      string

	data   map[string]interface{} //`json:"data" mapstructure:"data"`
	suffix string
	fl     *flock.Flock
	mu     sync.Mutex
}

const (
	FileCtxFormatDefault = "gob"
	FileCtxFormatGob     = "gob"
	FileCtxFormatJson    = "json"
	FileCtxFormatYaml    = "yaml"
)

// NewFileContext creates a new FileContext with the given context file.
// 如果可能包含敏感信息，请用 format=gob
func NewFileContext(contextFile string) *FileContext {
	var format string
	var suffix string
	if strings.HasSuffix(contextFile, ".yaml") {
		format = FileCtxFormatYaml
		suffix = ".yaml"
	} else if strings.HasSuffix(contextFile, ".json") {
		format = FileCtxFormatJson
		suffix = ".json"
	} else if strings.HasSuffix(contextFile, ".gob") {
		format = FileCtxFormatGob
		suffix = ".gob"
	} else {
		format = FileCtxFormatDefault
		suffix = ".gob"
		contextFile = contextFile + ".gob"
	}
	fc := &FileContext{
		format:      format,
		suffix:      suffix,
		contextFile: contextFile,
	}
	return fc
}

// NewFileContextWithFormat creates a new FileContext with the given context file prefix and format.
func NewFileContextWithFormat(contextFilePrefix string, format string) *FileContext {
	fc := &FileContext{
		format:      format,
		contextFile: contextFilePrefix,
	}
	switch format {
	case FileCtxFormatGob:
		fc.suffix = ".gob"
	case FileCtxFormatJson:
		fc.suffix = ".json"
	case FileCtxFormatYaml:
		fc.suffix = ".yaml"
	default:
		fc.suffix = ".gob"
	}
	fc.contextFile = contextFilePrefix + fc.suffix
	return fc
}

// GetContextFilePath returns the context file path.
func (c *FileContext) GetContextFilePath() string {
	return c.contextFile
}

// Decode read
func (c *FileContext) Decode(v interface{}) error {
	if err := mapstructure.Decode(c.data, v); err != nil {
		return err
	}
	return c.decodeData()
}

// Encode write
func (c *FileContext) Encode(v interface{}) error {
	if err := mapstructure.Decode(v, c.data); err != nil {
		return err
	}
	return c.encodeData()
}

// decodeData (read) decodes the FileContext struct from the disk file.
func (c *FileContext) decodeData() error {
	shareObj, err := os.ReadFile(c.contextFile)
	if err != nil {
		return errors.WithMessage(err, "read context file")
	}
	if strings.HasSuffix(c.contextFile, ".json") {
		if err = json.Unmarshal(shareObj, &c.data); err != nil {
			return err
		}
	} else if strings.HasSuffix(c.contextFile, ".yaml") {
		if err = yaml.Unmarshal(shareObj, &c.data); err != nil {
			return err
		}
	} else {
		if err = gob.NewDecoder(bytes.NewReader(shareObj)).Decode(&c.data); err != nil {
			return errors.WithMessage(err, "gob Decode FileContext")
		}
	}
	return nil
}

// encodeData (write) encodes the FileContext struct and writes it to the disk file.
func (c *FileContext) encodeData() error {
	if c.contextFile == "" {
		return errors.New("context file not given")
	}
	if c.data == nil {
		c.data = make(map[string]interface{})
	}

	var buf *bytes.Buffer
	if strings.HasSuffix(c.contextFile, ".json") {
		if bs, err := json.MarshalIndent(c.data, "", "  "); err != nil {
			//if bs, err := json.Marshal(c.data); err != nil {
			return err
		} else {
			buf = bytes.NewBuffer(bs)
		}
	} else if strings.HasSuffix(c.contextFile, ".yaml") {
		if bs, err := yaml.Marshal(c.data); err != nil {
			return err
		} else {
			buf = bytes.NewBuffer(bs)
		}
	} else {
		buf = bytes.NewBuffer(nil)
		if err := gob.NewEncoder(buf).Encode(c.data); err != nil {
			return errors.WithMessage(err, "gob Encode FileContext")
		}
	}

	fd, err := os.OpenFile(c.contextFile, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}

	defer fd.Close()
	if _, err = fd.Write(buf.Bytes()); err != nil {
		return err
	}
	return nil
}

// Get gets the value of the given key from the FileContext.
// if c.Data is empty or persistent is true, it will be decoded from the disk file.
func (c *FileContext) Get(key string, persistent bool) (interface{}, error) {
	if persistent {
		if err := c.decodeData(); err != nil {
			return nil, err
		}
	} else if c.data == nil {
		if err := c.decodeData(); err != nil {
			return nil, err
		}
		if c.data == nil {
			return nil, fmt.Errorf("context file %s is empty", c.contextFile)
		}
	}
	if val, ok := c.data[key]; ok {
		return val, nil
	} else {
		return nil, fmt.Errorf("key(%s) not found from context file %s", key, c.contextFile)
	}
}

// GetString gets the value of the given key from the FileContext and returns it as a string.
// try to get value from memory
func (c *FileContext) GetString(key string) (string, error) {
	val, err := c.Get(key, false)
	if err != nil {
		return "", err
	} else {
		return cast.ToStringE(val)
	}
}

// GetInt gets the value of the given key from the FileContext and returns it as an integer.
// try to get value from memory
func (c *FileContext) GetInt(key string) (int, error) {
	val, err := c.Get(key, false)
	if err != nil {
		return 0, err
	} else {
		return cast.ToIntE(val)
	}
}

// GetBool gets the value of the given key from the FileContext and returns it as a boolean.
func (c *FileContext) GetBool(key string) (bool, error) {
	val, err := c.Get(key, false)
	if err != nil {
		return false, err
	} else {
		return cast.ToBoolE(val)
	}
}

// GetValue decode value of key to v
// try to get value from memory
func (c *FileContext) GetValue(key string, v interface{}) error {
	val, err := c.Get(key, false)
	if err != nil {
		return err
	} else {
		return mapstructure.Decode(val, v)
	}
}

// GetStringPersistent gets the value of the given key from the FileContext and returns it as a string.
// get value from disk file
func (c *FileContext) GetStringPersistent(key string) (string, error) {
	val, err := c.Get(key, true)
	if err != nil {
		return "", err
	} else {
		return cast.ToStringE(val)
	}
}

// GetIntPersistent gets the value of the given key from the FileContext and returns it as an integer.
// get value from disk file
func (c *FileContext) GetIntPersistent(key string) (int, error) {
	val, err := c.Get(key, true)
	if err != nil {
		return 0, err
	} else {
		return cast.ToIntE(val)
	}
}

// GetBoolPersistent gets the value of the given key from the FileContext and returns it as a boolean.
// get value from disk file
func (c *FileContext) GetBoolPersistent(key string) (bool, error) {
	val, err := c.Get(key, true)
	if err != nil {
		return false, err
	} else {
		return cast.ToBoolE(val)
	}
}

// GetValuePersistent decode value of key to v
// always decode from disk file
func (c *FileContext) GetValuePersistent(key string, v interface{}) error {
	val, err := c.Get(key, true)
	if err != nil {
		return err
	} else {
		return mapstructure.Decode(val, v)
	}
}

// Save persistent the FileContext to the disk file.
func (c *FileContext) Save() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.encodeData()
}

// Set sets the value of the given key in the FileContext.
// if persistent is true, it will be encoded to the disk file.
func (c *FileContext) Set(key string, val interface{}, persist bool) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.data == nil {
		c.data = make(map[string]interface{})
	}
	c.data[key] = val
	if persist {
		return c.encodeData()
	}
	return nil
}

// Delete deletes the value of the given key from the FileContext.
// if persistent is true, it will be encoded to the disk file.
func (c *FileContext) Delete(key string, persistent bool) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.data == nil {
		c.data = make(map[string]interface{})
	}
	delete(c.data, key)
	if persistent {
		return c.encodeData()
	}
	return nil
}
