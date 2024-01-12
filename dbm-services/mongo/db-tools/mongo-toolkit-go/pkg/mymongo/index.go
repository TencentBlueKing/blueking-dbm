package mymongo

import (
	"context"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

// Collection the collection info
type Collection struct {
	DB      string
	C       string
	Indexes []bson.D
	Type    string
}

// GetIndexes get indexes
func GetIndexes(coll *mongo.Collection) (*mongo.Cursor, error) {
	return coll.Indexes().List(context.Background())
}

// todo dump index && restore index
// collection option

/*
func IndexDump(session *mongo.Client, DB, C string) error {
	meta := Metadata{}
	indexesIter, err := GetIndexes(session.Database(DB).Collection(C))
	if err != nil {
		return err
	}

	defer indexesIter.Close(context.Background())

	ctx := context.Background()
	for indexesIter.Next(ctx) {
		indexOpts := &bson.D{}
		err := indexesIter.Decode(indexOpts)
		if err != nil {
			return fmt.Errorf("error converting index: %v", err)
		}

		meta.Indexes = append(meta.Indexes, *indexOpts)
	}

	if err := indexesIter.Err(); err != nil {
		return fmt.Errorf("error getting indexes for collection `%s.%s`: %v", DB, C, err)
	}
}

*/
