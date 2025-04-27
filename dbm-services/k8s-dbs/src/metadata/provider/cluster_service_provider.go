package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sClusterServiceProvider interface {
	CreateClusterService(entity *entitys.K8sClusterServiceEntity) (*entitys.K8sClusterServiceEntity, error)
	DeleteClusterServiceById(id uint64) (uint64, error)
	FindClusterServiceById(id uint64) (*entitys.K8sClusterServiceEntity, error)
	UpdateClusterService(entity *entitys.K8sClusterServiceEntity) (uint64, error)
}

type K8sClusterServiceProviderImpl struct {
	dbAccess dbaccess.K8sClusterServiceDbAccess
}

func (k *K8sClusterServiceProviderImpl) CreateClusterService(entity *entitys.K8sClusterServiceEntity) (*entitys.K8sClusterServiceEntity, error) {
	newModel := models.K8sClusterServiceModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	addedModel, err := k.dbAccess.Create(&newModel)
	if err != nil {
		slog.Error("Failed to create model", "error", err)
		return nil, err
	} else {
		addedEntity := entitys.K8sClusterServiceEntity{}
		err := copier.Copy(&addedEntity, addedModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &addedEntity, nil
		}
	}
}

func (k *K8sClusterServiceProviderImpl) DeleteClusterServiceById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *K8sClusterServiceProviderImpl) FindClusterServiceById(id uint64) (*entitys.K8sClusterServiceEntity, error) {
	foundModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	} else {
		foundEntity := entitys.K8sClusterServiceEntity{}
		err := copier.Copy(&foundEntity, foundModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &foundEntity, nil
		}
	}
}

func (k *K8sClusterServiceProviderImpl) UpdateClusterService(entity *entitys.K8sClusterServiceEntity) (uint64, error) {
	newModel := models.K8sClusterServiceModel{}
	err := copier.Copy(&newModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&newModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sClusterServiceProvider(dbAccess dbaccess.K8sClusterServiceDbAccess) K8sClusterServiceProvider {
	return &K8sClusterServiceProviderImpl{dbAccess: dbAccess}
}
