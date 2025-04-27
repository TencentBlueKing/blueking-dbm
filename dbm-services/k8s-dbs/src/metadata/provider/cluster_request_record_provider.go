package provider

import (
	"k8s-dbs/src/metadata/dbaccess"
	models "k8s-dbs/src/metadata/dbaccess/model"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"log/slog"

	"github.com/jinzhu/copier"
)

type ClusterRequestRecordProvider interface {
	CreateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (*entitys.ClusterRequestRecordEntity, error)
	DeleteRequestRecordById(id uint64) (uint64, error)
	FindRequestRecordById(id uint64) (*entitys.ClusterRequestRecordEntity, error)
	UpdateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (uint64, error)
}

type ClusterRequestRecordProviderImpl struct {
	dbAccess dbaccess.ClusterRequestRecordDbAccess
}

func (k *ClusterRequestRecordProviderImpl) CreateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (*entitys.ClusterRequestRecordEntity, error) {
	newModel := models.ClusterRequestRecordModel{}
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
		addedEntity := entitys.ClusterRequestRecordEntity{}
		err := copier.Copy(&addedEntity, addedModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &addedEntity, nil
		}
	}
}

func (k *ClusterRequestRecordProviderImpl) DeleteRequestRecordById(id uint64) (uint64, error) {
	return k.dbAccess.DeleteById(id)
}

func (k *ClusterRequestRecordProviderImpl) FindRequestRecordById(id uint64) (*entitys.ClusterRequestRecordEntity, error) {
	foundModel, err := k.dbAccess.FindById(id)
	if err != nil {
		slog.Error("Failed to find entity")
		return nil, err
	} else {
		foundEntity := entitys.ClusterRequestRecordEntity{}
		err := copier.Copy(&foundEntity, foundModel)
		if err != nil {
			slog.Error("Failed to copy entity to copied model", "error", err)
			return nil, err
		} else {
			return &foundEntity, nil
		}
	}
}

func (k *ClusterRequestRecordProviderImpl) UpdateRequestRecord(entity *entitys.ClusterRequestRecordEntity) (uint64, error) {
	newModel := models.ClusterRequestRecordModel{}
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

func NewClusterRequestRecordProvider(dbAccess dbaccess.ClusterRequestRecordDbAccess) ClusterRequestRecordProvider {
	return &ClusterRequestRecordProviderImpl{dbAccess: dbAccess}
}
