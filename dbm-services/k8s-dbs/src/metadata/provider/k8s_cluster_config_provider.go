package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sClusterConfigProvider interface {
	CreateConfig(entity *entitys.K8sClusterConfigEntity) (*entitys.K8sClusterConfigEntity, error)
	DeleteConfigById(id uint64) (uint64, error)
	FindConfigById(id uint64) (*entitys.K8sClusterConfigEntity, error)
	FindConfigByName(name string) (*entitys.K8sClusterConfigEntity, error)
	UpdateConfig(entity *entitys.K8sClusterConfigEntity) (uint64, error)
}

type K8sClusterConfigProviderImpl struct {
	dbAccess dbaccess.K8sClusterConfigDbAccess
}

func (k *K8sClusterConfigProviderImpl) CreateConfig(entity *entitys.K8sClusterConfigEntity) (*entitys.K8sClusterConfigEntity, error) {
	configModel := models.K8sClusterConfigModel{}
	err := copier.Copy(&configModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	createdModel, err := k.dbAccess.Create(&configModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		configEntity := entitys.K8sClusterConfigEntity{}
		err := copier.Copy(&configEntity, createdModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &configEntity, nil
		}
	}
}

func (k *K8sClusterConfigProviderImpl) DeleteConfigById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sClusterConfigProviderImpl) FindConfigById(id uint64) (*entitys.K8sClusterConfigEntity, error) {
	configModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		configEntity := entitys.K8sClusterConfigEntity{}
		err := copier.Copy(&configEntity, configModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &configEntity, nil
		}
	}
}

func (k *K8sClusterConfigProviderImpl) FindConfigByName(name string) (*entitys.K8sClusterConfigEntity, error) {
	configModel, err := k.dbAccess.FindByClusterName(name)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		clusterEntity := entitys.K8sClusterConfigEntity{}
		err := copier.Copy(&clusterEntity, configModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &clusterEntity, nil
		}
	}
}

func (k *K8sClusterConfigProviderImpl) UpdateConfig(entity *entitys.K8sClusterConfigEntity) (uint64, error) {
	configModel := models.K8sClusterConfigModel{}
	err := copier.Copy(&configModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&configModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sClusterConfigProvider(dbAccess dbaccess.K8sClusterConfigDbAccess) K8sClusterConfigProvider {
	return &K8sClusterConfigProviderImpl{dbAccess}
}
