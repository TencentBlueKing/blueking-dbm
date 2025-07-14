/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package config

var Cfg = Configuration{}

// DiscoveryConfig discovery configuration
type DiscoveryConfig struct {
	Endpoints string `yaml:"endpoint" mapstructure:"endpoint"`
	User      string `yaml:"user"      mapstructure:"user"`
	Password  string `yaml:"password"  mapstructure:"password"`
}

// InputConfig define the information of data input stream.
type IntputConfig struct {
	Name      string   `yaml:"name"      mapstructure:"name"`
	Enable    bool     `yaml:"enable"    mapstructure:"enable"`
	Endpoints string   `yaml:"endpoint" mapstructure:"endpoint"`
	User      string   `yaml:"user"      mapstructure:"user"`
	Password  string   `yaml:"password"  mapstructure:"password"`
	Mechanism string   `yaml:"mechanism" mapstructure:"mechanism"`
	Topics    []string `yaml:"topics"    mapstructure:"topics"`
}

// OutputConfig Configuration related to data storage.
type OutputConfig struct {
	Name      string `yaml:"name"      mapstructure:"name"`
	Enable    bool   `yaml:"enable"    mapstructure:"enable"`
	Endpoints string `yaml:"endpoint" mapstructure:"endpoint"`
	User      string `yaml:"user"      mapstructure:"user"`
	Password  string `yaml:"password"  mapstructure:"password"`
}

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"      mapstructure:"path"`
	Level     string `yaml:"level"     mapstructure:"level"`
	FileCount int    `yaml:"fileCount" mapstructure:"fileCount"`
	FileSize  int    `yaml:"fileSize"  mapstructure:"fileSize"`
}

// Configuration receiver's configuration
type Configuration struct {
	Name      string          `yaml:"name"      mapstructure:"name"`
	Version   string          `yaml:"version"   mapstructure:"version"`
	Discovery DiscoveryConfig `yaml:"discovery" mapstructure:"discovery"`
	Inputers  []IntputConfig  `yaml:"input"     mapstructure:"input"`
	Outputers []OutputConfig  `yaml:"output"    mapstructure:"output"`
	Log       LogConfig       `yaml:"log"       mapstructure:"log"`
}
