package mongologparser

import (
	"encoding/json"
	"fmt"
	"testing"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

func TestParseV2Log(t *testing.T) {
	// test cases
	in := [][]byte{
		[]byte("2024-03-04T23:05:20.854+0800 I -        [conn5343139] end connection 1.1.1.1:50908 (5 connections now open)"),
		[]byte("2024-11-25T05:52:36.348+0800 I ACCESS   [conn38] Successfully authenticated as principal monitor on adminxyz"),
	}
	for _, line := range in {
		p, err := GetParser(line)
		if err != nil {
			fmt.Printf("failed to get parser: %s\n", err)
			continue
		}
		msg, err := p.Parse(line)
		t.Logf("p %+v msg %+v, err :%v", p.Name(), msg, err)
	}

}

func TestParseV2SlowLog(t *testing.T) {
	// test cases
	in := [][]byte{
		[]byte("2024-03-26T18:05:46.292+0800 I WRITE    [conn191216] insert xxxxx.actor_wenzhang_data query: { _id: ObjectId('66029df8582c07041b54d4e9'), exp: 0, pos: 0, card_id: 0, cfg_id: 20104, level: 1, actor_id: 1074635, id: 476755 } ninserted:1 keyUpdates:0 writeConflicts:0 numYields:0 locks:{ Global: { acquireCount: { r: 2, w: 2 } }, Database: { acquireCount: { w: 2 } }, Collection: { acquireCount: { w: 1 } }, oplog: { acquireCount: { w: 1 } } } 1318ms"),
		[]byte(`2024-03-26T15:38:16.032+0800 I COMMAND  [conn190722] warning: log line attempted (54k) over max size (10k), printing beginning and end ... command lzjd_game_14.$cmd command: delete { delete: "battle_data_restore", deletes: [ { q: { id: { $in: [ 152309515, 152309535, 152309555, 152309575, 152309595, 152309935, 152309955, 152309975, 152309995, 152310015, 152310035, 152310055, 152310075, 152310095, 152310115, 152310135, 152310155, 152310175, 152310195, 152310215, 152310235, 152310255, 152310275, 152310295, 152310315, 152310335, 152310355, 152310375, 152310395, 152310415, 152310435, 152310455, 152310475, 152310495, 152310515, 152310535, 152310555, 152310575, 152310595, 152310615, 152310635, 152310655, 152310675, 152310695, 152310715, 152310735, 152310755, 152310775, 152310795, 152310815, 152310835, 152310855, 152310875, 152310895, 152310915, 152310935, 152310955, 152310975, 152310995, 152311015, 152311035, 152311055, 152311075, 152311095, 152311115, 152311135, 152311155, 152311175, 152311195, 152311215, 152311235, 152311255, 152311275, 152311295, 152311315, 152311335, 152311355, 152311375, 152311395, 152311415, 152311435, 152311455, 152311475, 152311495, 152311515, 152311535, 152311555, 152311575, 152311595, 152311615, 152311635, 152311655, 152311675, 152311695, 152311715, 152311735, 152311755, 152311775, 152311795, 152311815, 152311835, 152311855, 152311875, 152311895, 152311915, 152311935, 152311955, 152311975, 152311995, 152312015, 152312035, 152312055, 152312275, 152312295, 152312355, 152312375, 152312395, 152312415, 152312435, 152312455, 152312475, 152312495, 152312515, 152312535, 152312555, 152312575, 152312595, 152312615, 152312635, 152312655, 152312675, 152312695, 152312715, 152312735, 152312755, 152312775, 152312795, 152312815, 152312835, 152312855, 152312875, 152312895, 152312915, 152312935, 152312955, 152312975, 152312995, 152313015, 152313035, 152313055, 152313075, 152313095, 152313115, 152313135, 152313155, 152313175, 152313195, 152313215, 152313235, 152313255, 152313275, 152313295, 152313315, 152313335, 152313355, 152313375, 152313395, 152313415, 152313435, 152313735, 152313755, 152313775, 152313795, 152313815, 152313835, 152313855, 152313875, 152313895, 152313915, 152313975, 152314195, 152314215, 152314235, 152314255, 152314275, 152314295, 152314315, 152314335, 152314355, 152314375, 152314395, 152314735, 152314755, 152314775, 152314795, 152314815, 152314835, 152314855, 152314875, 152314895, 152314915, 152314935, 152314955, 152314975, 152314995, 152315015, 152315035, 152315055, 152315075, 152315095, 152315115, 152315135, 152315155, 152315175, 152315195, 152315215, 152315235, 152315255, 152315275, 152315295, 152315315, 152315335, 152315355, 152315375, 152315395, 152315415, 152315435, 152315455, 152315475, 152315495, 152315515, 152315535, 152315555, 152315575, 152315595, 152315615, 152315635, 152315655, 152315675, 152315695, 152315715, 152315735, 152315755, 152315775, 152315795, 152315815, 152315835, 152315855, 152315875, 152315895, 152315915, 152315935, 152315955, 152315975, 152315995, 152316015, 152316035, 152316055, 152316075, 152316095, 152316115, 152316135, 152316155, 152316175, 152316195, 152316215, 152316235, 152316255, 152316275, 152316295, 152316315, 152316335, 152316615, 152316635, 152316655, 152316675, 152316695, 152316715, 152316835, 152317035, 152317055, 152317075, 152317095, 152317115, 152317135, 152317155, 152317175, 152317195, 152317215, 152317235, 152317255, 152317275, 152317295, 152317315, 152317335, 152317355, 152317375, 152317395, 152317415, 152317435, 1523174 ..........  152467935, 152467955, 152468215, 152468235, 152468255, 152468275, 152468295, 152468315, 152468335, 152468355, 152468615, 152468795, 152468895, 152468915, 152468935, 152468955, 152468975, 152468995, 152469015, 152469035, 152469055, 152469075, 152469095, 152469115, 152469135, 152469155, 152469175, 152469195, 152469215, 152469235, 152469255, 152469275, 152469295, 152469315, 152469335, 152469355, 152469375, 152469395, 152469415, 152469435, 152469455, 152469715, 152469735, 152469755, 152469775, 152469795, 152469815, 152469835, 152470095, 152470115, 152470135, 152470155, 152470175, 152470195, 152470215, 152470235, 152470255, 152470275, 152470295, 152470315, 152470335, 152470615, 152470635, 152470655, 152470675, 152470695, 152470715, 152470735, 152470755, 152470775, 152470795, 152470815, 152470835, 152470855, 152470875, 152471135, 152471155, 152471175, 152471195, 152471215, 152471235, 152471255, 152471275, 152471295, 152471315, 152471415, 152471595, 152471615, 152471635, 152471655, 152471675, 152471695, 152471715, 152471735, 152471755, 152471775, 152471795, 152471815, 152471835, 152471855, 152471875, 152471895, 152471915, 152471935, 152471955, 152471975, 152471995, 152472015, 152472035, 152472055, 152472075, 152472095, 152472115, 152472135, 152472155, 152472175, 152472195, 152472215, 152472235, 152472255, 152472275, 152472295, 152472315, 152472335, 152472355, 152472375, 152472395, 152472415, 152472435, 152472455, 152472475, 152472495, 152472515, 152472535, 152472555, 152472575, 152472595, 152472615, 152472635, 152472655, 152472675, 152472695, 152472715, 152472735, 152472755, 152472775, 152472795, 152472815, 152472835, 152472855, 152472875, 152472895, 152472915, 152473195, 152473215, 152473475, 152473495, 152473515, 152473535, 152473555, 152473575, 152473595, 152473615, 152473635, 152473655, 152473675, 152473695, 152473715, 152473815, 152473835, 152473855, 152473875, 152473895, 152473915, 152473935, 152473955, 152473975, 152473995, 152474015, 152474275, 152474295, 152474315, 152474335, 152474355, 152474375, 152474395, 152474415, 152474435, 152474455, 152474475, 152474495, 152474515, 152474535, 152474555, 152474575, 152474595, 152474615, 152474635, 152474895, 152474915, 152474935, 152474955, 152474975, 152474995, 152475015, 152475035, 152475055, 152475075, 152475095, 152475115, 152475135, 152475155, 152475175, 152475195, 152475215, 152475235, 152475255, 152475275, 152475295, 152475315, 152475335, 152475355, 152475375, 152475395, 152475415, 152475435, 152475455, 152476075, 152476095, 152476115, 152476135, 152476155, 152476175, 152476195, 152476215, 152476475, 152476495, 152476515, 152476535, 152476555, 152476575, 152476595, 152476615, 152476635, 152476655, 152476675, 152476695, 152476715, 152476735, 152476755, 152476775, 152476795, 152476815, 152476835, 152476855, 152476875, 152476895, 152476915, 152476935, 152476955, 152476975, 152476995, 152477015, 152477035, 152477055, 152477075, 152477095, 152477115, 152477135, 152477155, 152477175, 152477195, 152477215, 152477235, 152477255, 152477275, 152477295, 152477315, 152477335, 152477355, 152477375, 152477395, 152477415, 152477435 ] } }, limit: 0 } ], ordered: true, writeConcern: {} } keyUpdates:0 writeConflicts:0 numYields:0 reslen:80 locks:{ Global: { acquireCount: { r: 5120, w: 5120 } }, Database: { acquireCount: { w: 5120 } }, Collection: { acquireCount: { w: 41 } }, oplog: { acquireCount: { w: 5079 } } } 367ms`),
		[]byte(`2024-03-26T10:11:46.240+0800 I COMMAND  [conn652482] command xxxxx.yyyy command: find { find: "node_247", filter: { copyFromCredentialsKey: { $ne: null }, _id: { $gt: ObjectId('000000000000000000000000') } }, sort: { _id: 1 }, projection: { copyIntoCredentialsKey: 1, sha256: 1, repoName: 1, copyFromCredentialsKey: 1, id: 1, projectId: 1 }, limit: 1000, $db: "bkrepo_prod", $readPreference: { mo^Cde: "secondaryPreferred" } } planSummary: IXSCAN { _id: 1 } keysExamined:669527 docsExamined:669527 cursorExhausted:1 numYields:5233 nreturned:0 reslen:93 locks:{ Global: { acquireCount: { r: 10468 }, acquireWaitCount: { r: 4958 }, timeAcquiringMicros: { r: 18781173 } }, Database: { acquireCount: { r: 5234 } }, Collection: { acquireCount: { r: 5234 } } } protocol:op_msg 46719ms`),
		[]byte(`2024-03-28T05:33:43.053+0800 I COMMAND  [conn9133507] serverStatus was very slow: { after basic: 0, after asserts: 0, after connections: 0, after cursors: 0, after extra_info: 0, after globalLock: 0, after locks: 0, after network: 0, after opcounters: 0, after opcountersRepl: 0, after repl: 0, after storageEngine: 0, after wiredTiger: 2854, at end: 2854 }`),
		[]byte(`2024-05-06T00:53:41.914+0800 I COMMAND  [conn392119439] CMD: dropIndexes cmdb.cc_ObjClassification: "bk_classification_name_1"`),
		[]byte(`2024-05-03T06:06:12.917+0800 I QUERY    [ClusterCursorCleanupJob] Marking cursor id 781425902501866090 for deletion, idle since 2024-05-03T05:56:09.762+0800`),
		[]byte(`2024-05-06T08:10:06.332+0800 I COMMAND  [conn77742] query xxxxx.yyyy query: { base_handbook_id: 100231 } planSummary: IXSCAN { base_handbook_id: 1 } ntoskip:0 nscanned:0 nscannedObjects:0 keyUpdates:0 writeConflicts:0 numYields:0 nreturned:0 reslen:20 locks:{ Global: { acquireCount: { r: 2 } }, Database: { acquireCount: { r: 1 } }, Collection: { acquireCount: { r: 1 } } } 584ms`),
	}
	for _, line := range in {
		p, err := GetParser(line)
		if err != nil {
			fmt.Printf("failed to get parser: %s\n", err)
			continue
		}
		msg, err := p.Parse(line)
		msgJson, _ := json.Marshal(msg)
		t.Logf("p %+v msg %s, err :%v", p.Name(), msgJson, err)
	}

}

func TestDateTimeStruct(t *testing.T) {
	var v primitive.DateTime
	o, err := v.MarshalJSON()
	if err != nil {
		t.Errorf("%s %v", o, err)
	} else {
		t.Logf("%s %v", o, err)

	}
}

func TestParseV3Log(t *testing.T) {
	// test cases
	in := [][]byte{
		[]byte(`{"t":{"$date":"2025-02-24T09:21:08.172+08:00"},"s":"I",  "c":"NETWORK",  "id":22944,   "ctx":"conn31436","msg":"Connection ended","attr":{"remote":"1.1.1.1:22918","uuid":"c022b41c-3420-4a96-883e-15203170b0f3","connectionId":31436,"connectionCount":4}}`),
		[]byte(`{"t":{"$date":"2024-04-12T19:30:50.102+08:00"},"s":"I",  "c":"NETWORK",  "id":22943,   "ctx":"listener","msg":"Connection accepted","attr":{"remote":"1.1.1.1:43937","connectionId":36613903,"connectionCount":5853}}`),
		[]byte(`{"t":{"$date":"2024-04-15T07:00:02.197+08:00"},"s":"I",  "c":"COMMAND",  "id":51803,   "ctx":"conn2951774","msg":"Slow query","attr":{"type":"command","ns":"game.tradebaseprices","appName":"MongoDB Shell","command":{"getMore":5717084478745951296,"collection":"tradebaseprices","$clusterTime":{"clusterTime":{"$timestamp":{"t":1713135601,"i":9736}},"signature":{"hash":{"$binary":{"base64":"jdJpfCvs3QxE7po7HrcoYnA7yDs=","subType":"0"}},"keyId":7294760626633572548}},"$audit":{"$impersonatedUsers":[{"user":"game","db":"admin"}],"$impersonatedRoles":[{"role":"root","db":"admin"},{"role":"readWrite","db":"admin"},{"role":"readWriteAnyDatabase","db":"admin"}]},"$client":{"application":{"name":"MongoDB Shell"},"driver":{"name":"MongoDB Internal Client","version":"3.4.10"},"os":{"type":"Linux","name":"Tencent tlinux release 2.2 (Final)","architecture":"x86_64","version":"Kernel 3.10.107-1-tlinux2_kvm_guest-0051"},"mongos":{"host":"xxxxx:27021","client":"1.1.1.1:42362","version":"4.4.25"}},"$configServerState":{"opTime":{"ts":{"$timestamp":{"t":1713135600,"i":6299}},"t":12}},"$db":"game"},"originatingCommand":{"aggregate":"tradebaseprices","pipeline":[{"$sort":{"spid":1,"created_at":1}},{"$project":{"prices":true,"spid":true,"_id":false}}],"allowDiskUse":true,"fromMongos":true,"needsMerge":true,"collation":{"locale":"simple"},"cursor":{"batchSize":0},"runtimeConstants":{"localNow":{"$date":"2024-04-14T23:00:01.474Z"},"clusterTime":{"$timestamp":{"t":1713135601,"i":9484}}},"use44SortKeys":true,"useNewUpsert":true,"readConcern":{"provenance":"implicitDefault"},"writeConcern":{"w":1,"wtimeout":0,"provenance":"implicitDefault"},"shardVersion":[{"$timestamp":{"t":128,"i":0}},{"$oid":"61e599f7a065d7e247a7bb53"}],"clientOperationKey":{"$uuid":"d6a23d7a-ca01-4b02-9a2b-4ccb934f9560"},"$readPreference":{"mode":"secondary"},"$clusterTime":{"clusterTime":{"$timestamp":{"t":1713135601,"i":9590}},"signature":{"hash":{"$binary":{"base64":"jdJpfCvs3QxE7po7HrcoYnA7yDs=","subType":"0"}},"keyId":7294760626633572548}},"$audit":{"$impersonatedUsers":[{"user":"game","db":"admin"}],"$impersonatedRoles":[{"role":"root","db":"admin"},{"role":"readWrite","db":"admin"},{"role":"readWriteAnyDatabase","db":"admin"}]},"$client":{"application":{"name":"MongoDB Shell"},"driver":{"name":"MongoDB Internal Client","version":"3.4.10"},"os":{"type":"Linux","name":"Tencent tlinux release 2.2 (Final)","architecture":"x86_64","version":"Kernel 3.10.107-1-tlinux2_kvm_guest-0051"},"mongos":{"host":"27021","client":"1.1.1.1:42362","version":"4.4.25"}},"$configServerState":{"opTime":{"ts":{"$timestamp":{"t":1713135601,"i":7126}},"t":12}},"$db":"game"},"planSummary":"COLLSCAN","cursorid":5717084478745951296,"keysExamined":0,"docsExamined":130566,"hasSortStage":true,"numYields":235,"nreturned":104984,"reslen":16777509,"locks":{"FeatureCompatibilityVersion":{"acquireCount":{"r":236}},"ReplicationStateTransition":{"acquireCount":{"w":236}},"Global":{"acquireCount":{"r":236}},"Database":{"acquireCount":{"r":236}},"Collection":{"acquireCount":{"r":236}},"Mutex":{"acquireCount":{"r":1}}},"readConcern":{"provenance":"implicitDefault"},"writeConcern":{"w":1,"wtimeout":0,"provenance":"implicitDefault"},"storage":{"data":{"bytesRead":34508234,"timeReadingMicros":37413}},"protocol":"op_msg","durationMillis":707}}`),
		[]byte(`{"t":{"$date":"2024-04-29T18:04:28.239+08:00"},"s":"I",  "c":"COMMAND",  "id":51803,   "ctx":"conn15148443","msg":"Slow query","attr":{"type":"query","ns":"game.tradesellorders","command":{"find":"tradesellorders","filter":{"aid":{"$oid":"5fd8d1a8b4396631a4bbc6b0"}},"$db":"game"},"nShards":64,"cursorExhausted":true,"numYields":0,"nreturned":0,"reslen":249,"durationMillis":105}}`),
	}
	for _, line := range in {

		p, err := GetParser(line)
		if err != nil {
			fmt.Printf("failed to get parser: %s\n", err)
			continue
		}
		msg, err := p.Parse(line)
		t.Logf("p %+v msg %+v, err :%v", p.Name(), msg, err)

	}

}

func TestParseV1Log(t *testing.T) {
	// test cases
	in := []byte(`Fri Apr 12 04:16:54.496 [conn9818835] getmore xxxx.xxxxxx query: { query: {}, $snapshot: true } cursorid:7678192233559697393 ntoreturn:0 exhaust:1 keyUpdates:0 numYields: 5 locks(micros) r:344667 nreturned:22 reslen:4255713 260ms`)
	msg, err := ParseV1Log(in)
	if err != nil {
		t.Errorf("ParseV2Log(%s) failed: %v", in, err)
	} else {
		t.Logf("ParseV2Log(%s)", in)
		v, _ := json.Marshal(msg)
		t.Logf("json (%s)", v)

	}
}
