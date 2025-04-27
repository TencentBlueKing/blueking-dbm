package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type K8sCrdOpsRequestProvider interface {
	CreateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (*entitys.K8sCrdOpsRequestEntity, error)
	DeleteOpsRequestById(id uint64) (uint64, error)
	FindOpsRequestById(id uint64) (*entitys.K8sCrdOpsRequestEntity, error)
	UpdateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (uint64, error)
}

type K8sCrdOpsRequestProviderImpl struct {
	dbAccess dbaccess.K8sCrdOpsRequestDbAccess
}

func (k K8sCrdOpsRequestProviderImpl) CreateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (*entitys.K8sCrdOpsRequestEntity, error) {
	k8sOpsRequestModel := models.K8sCrdOpsRequestModel{}
	err := copier.Copy(&k8sOpsRequestModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return nil, err
	}
	opsModel, err := k.dbAccess.Create(&k8sOpsRequestModel)
	if err != nil {
		slog.Error("Failed to create entity", "error", err)
		return nil, err
	} else {
		opsEntity := entitys.K8sCrdOpsRequestEntity{}
		err := copier.Copy(&opsEntity, opsModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &opsEntity, nil
		}
	}
}

func (k K8sCrdOpsRequestProviderImpl) DeleteOpsRequestById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k K8sCrdOpsRequestProviderImpl) FindOpsRequestById(id uint64) (*entitys.K8sCrdOpsRequestEntity, error) {
	opsModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to delete entity", "error", err)
		return nil, err
	} else {
		opsEntity := entitys.K8sCrdOpsRequestEntity{}
		err := copier.Copy(&opsEntity, opsModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &opsEntity, nil
		}
	}
}

func (k K8sCrdOpsRequestProviderImpl) UpdateOpsRequest(entity *entitys.K8sCrdOpsRequestEntity) (uint64, error) {
	opsRequestModel := models.K8sCrdOpsRequestModel{}
	err := copier.Copy(&opsRequestModel, entity)
	if err != nil {
		slog.Error("Failed to copy entity to copied model", "error", err)
		return 0, err
	}
	rows, err := k.dbAccess.Update(&opsRequestModel)
	if err != nil {
		slog.Error("Failed to update entity", "error", err)
		return 0, err
	} else {
		return rows, nil
	}
}

func NewK8sCrdOpsRequestProvider(dbAccess dbaccess.K8sCrdOpsRequestDbAccess) K8sCrdOpsRequestProvider {
	return &K8sCrdOpsRequestProviderImpl{dbAccess}
}
