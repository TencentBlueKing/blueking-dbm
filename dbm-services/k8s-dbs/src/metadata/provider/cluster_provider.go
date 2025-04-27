package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdClusterProvider interface {
	CreateCluster(entity *entitys.K8sCrdClusterEntity) (*entitys.K8sCrdClusterEntity, error)
	DeleteClusterById(id uint64) (uint64, error)
	FindClusterById(id uint64) (*entitys.K8sCrdClusterEntity, error)
	FindByParams(params map[string]interface{}) (*entitys.K8sCrdClusterEntity, error)
	UpdateCluster(entity *entitys.K8sCrdClusterEntity) (uint64, error)
}

type K8sCrlClusterProviderImpl struct {
	dbAccess dbaccess.K8sCrdClusterDbAccess
}

func (k *K8sCrlClusterProviderImpl) CreateCluster(entity *entitys.K8sCrdClusterEntity) (*entitys.K8sCrdClusterEntity, error) {
	k8sCrdClusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&k8sCrdClusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	clusterModel, err := k.dbAccess.Create(&k8sCrdClusterModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		clusterEntity := entitys.K8sCrdClusterEntity{}
		err := copier.Copy(&clusterEntity, clusterModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &clusterEntity, nil
		}
	}
}

func (k *K8sCrlClusterProviderImpl) DeleteClusterById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sCrlClusterProviderImpl) FindClusterById(id uint64) (*entitys.K8sCrdClusterEntity, error) {
	clusterModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		clusterEntity := entitys.K8sCrdClusterEntity{}
		err := copier.Copy(&clusterEntity, clusterModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &clusterEntity, nil
		}
	}
}

func (k *K8sCrlClusterProviderImpl) FindByParams(params map[string]interface{}) (*entitys.K8sCrdClusterEntity, error) {
	clusterModel, err := k.dbAccess.FindByParams(params)
	if err != nil {
		slog.Error("Failed to find entity", "error", err)
		return nil, err
	} else {
		clusterEntity := entitys.K8sCrdClusterEntity{}
		err := copier.Copy(&clusterEntity, clusterModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &clusterEntity, nil
		}
	}
}

func (k *K8sCrlClusterProviderImpl) UpdateCluster(entity *entitys.K8sCrdClusterEntity) (uint64, error) {
	clusterModel := models.K8sCrdClusterModel{}
	err := copier.Copy(&clusterModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&clusterModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdClusterProvider(dbAccess dbaccess.K8sCrdClusterDbAccess) K8sCrdClusterProvider {
	return &K8sCrlClusterProviderImpl{dbAccess}
}
