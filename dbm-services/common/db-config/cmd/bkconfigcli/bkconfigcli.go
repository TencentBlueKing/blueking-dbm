package main

import (
	"encoding/json"
	"fmt"
	"strings"

	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/util/crypt"

	"github.com/jinzhu/copier"
	"github.com/manifoldco/promptui"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"gorm.io/gorm"
)

var queryCmd = &cobra.Command{
	Use:   "query",
	Short: "query sensitive values such as password",
	Long:  `query sensitive values such as password, may use with --decrypt`,
	RunE: func(cmd *cobra.Command, args []string) error {
		confItems := make([]ConfItemsResp, 0)
		var err error
		decrypt := config.GetBool("decrypt")
		// 查询密码解密 key 优先从命令行 old-key 获取，如果为空，则从配置文件 encrypt.keyPrefix 获取
		keyPrefix := config.GetString("old-key")
		if keyPrefix == "" {
			keyPrefix = config.GetString("encrypt.keyPrefix")
		}
		BkBizId := config.GetInt("bk-biz-id")
		if BkBizId == 0 {
			fmt.Printf("query plat's default config values(tb_config_name_def) using key=%s\n", keyPrefix)
			confItems, err = queryEncryptConfNames(decrypt, keyPrefix, model.DB.Self)
		} else {
			fmt.Printf("query bk_biz_id=%d config values (tb_config_node) using key=%s\n", BkBizId, keyPrefix)
			confItems, err = queryEncryptConfValues(decrypt, keyPrefix, model.DB.Self)
		}
		var jsonBytes []byte
		jsonBytes, _ = json.Marshal(confItems)
		fmt.Printf("\n%+v\n", string(jsonBytes))

		if err != nil {
			return err
		}
		return nil
	},
}

var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "update password with new encrypt key. you should backup it with query command",
	Long:  `update password with new encrypt key, may use with --old-key xxx --new-key yyy`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		var confItems []ConfItemsResp
		var rowsAffected int64
		// 旧 key 从命令行参数 --old-key 获取
		// 新 key 会优先从从命令参数 --new-key 获取，如果为空，则从配置文件获取 encrypt.keyPrefix
		oldKeyPrefix := config.GetString("old-key")
		newKeyPrefix := config.GetString("new-key")
		if newKeyPrefix == "" {
			newKeyPrefix = config.GetString("encrypt.keyPrefix")
		}
		if oldKeyPrefix == newKeyPrefix {
			return errors.Errorf("old key and new key is the same: %s", oldKeyPrefix)
		}
		BkBizId := config.GetInt("bk-biz-id")
		if BkBizId == 0 {
			confItems, err = queryEncryptConfNames(true, oldKeyPrefix, model.DB.Self)
			if err != nil {
				return err
			}
			fmt.Printf("update plat's default config values(tb_config_name_def), Count:%d\n", len(confItems))
			prompt := promptui.Prompt{
				Label:     fmt.Sprintf("Are you sure to update key with new=%s, old=%s ", newKeyPrefix, oldKeyPrefix),
				IsConfirm: true,
				Default:   "N",
			}
			promptRes, _ := prompt.Run()
			if strings.ToLower(promptRes) == "y" {
				rowsAffected, err = updateEncryptConfNames(newKeyPrefix, confItems, model.DB.Self)
			} else {
				fmt.Println("quit")
			}
		} else {
			confItems, err = queryEncryptConfValues(true, oldKeyPrefix, model.DB.Self)
			if err != nil {
				return err
			}
			fmt.Printf("update bk_biz_id=%d config values (tb_config_node), Count:%d\n", BkBizId, len(confItems))
			prompt := promptui.Prompt{
				Label:     fmt.Sprintf("Are you sure to update key with new=%s, old=%s ", newKeyPrefix, oldKeyPrefix),
				IsConfirm: true,
				Default:   "N",
			}
			promptRes, _ := prompt.Run()
			if strings.ToLower(promptRes) == "y" {
				rowsAffected, err = updateEncryptConfValues(newKeyPrefix, confItems, model.DB.Self)
			} else {
				fmt.Println("quit")
			}
		}
		fmt.Printf("rowsAffected:%d\n", rowsAffected)
		return err
	},
}

// ConfItemsResp copied from model.ConfigNameDefModel
type ConfItemsResp struct {
	ID        uint64 `json:"id"`
	Namespace string `json:"namespace"`
	ConfType  string `json:"conf_type"`
	ConfFile  string `json:"conf_file"`
	ConfName  string `json:"conf_name"`
	//ConfNameLC   string `json:"conf_name_lc"`
	ValueDefault string `json:"value_default"`
	ValueType    string `json:"value_type"`
	ValueTypeSub string `json:"value_type_sub"`
	ValueAllowed string `json:"value_allowed"`
	FlagLocked   int8   `json:"flag_locked"`
	FlagEncrypt  int8   `json:"flag_encrypt"`
	//FlagDisable  int8   `json:"flag_disable"`
	FlagStatus int8 `json:"flag_status"`

	ConfValue  string `json:"conf_value"`
	LevelName  string `json:"level_name"`
	LevelValue string `json:"level_value"`
}

func queryEncryptConfNames(decrypt bool, keyPrefix string, db *gorm.DB) ([]ConfItemsResp, error) {
	confNames := make([]*model.ConfigNameDefModel, 0)
	sqlRes := db.Model(model.ConfigNameDefModel{}).
		Select("id", "namespace", "conf_type", "conf_file", "conf_name", "value_default").
		Where("flag_encrypt = 1 and value_default not like '{{%'")
	if namespace := config.GetString("namespace"); namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if confType := config.GetString("conf-type"); confType != "" {
		sqlRes = sqlRes.Where("conf_type = ?", confType)
	}
	if confFile := config.GetString("conf-file"); confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	if names := config.GetStringSlice("conf_name"); len(names) != 0 {
		sqlRes = sqlRes.Where("conf_name in ?", names)
	}

	var err error
	if err = sqlRes.Find(&confNames).Error; err != nil {
		return nil, err
	}
	confItems := make([]ConfItemsResp, 0)
	var errDecrypt bool
	key := fmt.Sprintf("%s%s", keyPrefix, constvar.BKBizIDForPlat)
	for _, cn := range confNames {
		if decrypt {
			cn.ValueDefault, err = crypt.DecryptString(cn.ValueDefault, key, constvar.EncryptEnableZip)
			if err != nil {
				fmt.Printf("error %s: %+v\n", err.Error(), cn)
				errDecrypt = true
				continue
			}
		}
		var one = &ConfItemsResp{}
		copier.Copy(one, cn)
		confItems = append(confItems, *one)
	}
	if errDecrypt {
		return confItems, errno.ErrDecryptValue
	}

	return confItems, nil
}

// updateEncryptConfNames godoc
func updateEncryptConfNames(keyPrefix string, confItems []ConfItemsResp, db *gorm.DB) (int64, error) {
	var err error
	var rowsAffected int64
	newKey := fmt.Sprintf("%s%s", keyPrefix, constvar.BKBizIDForPlat)
	err = db.Transaction(func(tx *gorm.DB) error {
		for _, conf := range confItems {
			newValue, err := crypt.EncryptString(conf.ValueDefault, newKey, constvar.EncryptEnableZip)
			if err != nil {
				return errors.Wrapf(err, "%+v", conf)
			}
			updateVal := tx.Model(model.ConfigNameDefModel{}).Where("id = ?", conf.ID).
				UpdateColumn("value_default", newValue)
			if updateVal.Error != nil {
				return errors.Wrapf(updateVal.Error, "%+v", conf)
			}
			if updateVal.RowsAffected != 1 {
				return errors.Errorf("expect 1 row affected, but got %d: %+v", updateVal.RowsAffected, conf)
			} else {
				rowsAffected += updateVal.RowsAffected
			}
		}
		return nil
	})
	return rowsAffected, err
}

// updateEncryptConfValues godoc
func updateEncryptConfValues(keyPrefix string, confItems []ConfItemsResp, db *gorm.DB) (int64, error) {
	var rowsAffected int64
	err := db.Transaction(func(tx *gorm.DB) error {
		for _, conf := range confItems {
			newKey := fmt.Sprintf("%s%s", keyPrefix, conf.LevelValue)
			newValue, err := crypt.EncryptString(conf.ConfValue, newKey, constvar.EncryptEnableZip)
			if err != nil {
				return errors.Wrapf(err, "%+v", conf)
			}
			updateVal := tx.Model(model.ConfigModel{}).Where("id = ?", conf.ID).
				UpdateColumn("conf_value", newValue)
			if updateVal.Error != nil {
				return errors.Wrapf(updateVal.Error, "%+v", conf)
			}
			if updateVal.RowsAffected != 1 {
				return errors.Errorf("expect 1 row affected, but got %d: %+v", updateVal.RowsAffected, conf)
			} else {
				rowsAffected += updateVal.RowsAffected
			}
		}
		return nil
	})
	return rowsAffected, err
}

func queryEncryptConfValues(decrypt bool, keyPrefix string, db *gorm.DB) ([]ConfItemsResp, error) {
	confItems := make([]*model.ConfigModel, 0)
	sqlRes := db.Model(model.ConfigModel{}).
		Select("id", "namespace", "conf_type", "conf_file", "conf_name", "conf_value", "level_name", "level_value").
		Where("conf_value like '**%'")
	if namespace := config.GetString("namespace"); namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if confType := config.GetString("conf-type"); confType != "" {
		sqlRes = sqlRes.Where("conf_type = ?", confType)
	}
	if confFile := config.GetString("conf-file"); confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	BkBizId := config.GetInt("bk-biz-id")
	if BkBizId != -1 { // bk-biz-id(bk_biz_id) = -1 means query all
		sqlRes = sqlRes.Where("bk_biz_id = ?", BkBizId)
	} else if BkBizId == 0 {
		return nil, errors.Errorf("bk_biz_id cannot be 0 when quering tb_config_node")
	}

	if names := config.GetStringSlice("conf_name"); len(names) != 0 {
		sqlRes = sqlRes.Where("conf_name in ?", names)
	}

	var err error
	if err = sqlRes.Find(&confItems).Error; err != nil {
		return nil, err
	}

	confValues := make([]ConfItemsResp, 0)
	var errDecrypt bool
	for _, cn := range confItems {
		if decrypt {
			key := fmt.Sprintf("%s%s", keyPrefix, cn.LevelValue)
			cn.ConfValue, err = crypt.DecryptString(cn.ConfValue, key, constvar.EncryptEnableZip)
			if err != nil {
				fmt.Printf("error %s: %+v\n", err.Error(), cn)
				errDecrypt = true
				continue
			}
		}
		var one = &ConfItemsResp{}
		copier.Copy(one, cn)
		confValues = append(confValues, *one)
	}
	if errDecrypt {
		return confValues, errno.ErrDecryptValue
	}
	return confValues, nil
}
