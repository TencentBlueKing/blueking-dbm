package common

// NodeHiddenTrueScript 隐藏节点
var NodeHiddenTrueScript = `
var host='{{host}}';
var cfg=rs.conf();
cfg.members.forEach(function (member) {
    if (member.host == host ) {
		member.priority=0;
		member.hidden={{hidden}};
    }
});
rs.reconfig(cfg);
`

// NodeHiddenFalseScript 开放节点
var NodeHiddenFalseScript = `
var host='{{host}}';
var cfg=rs.conf();
cfg.members.forEach(function (member) {
    if (member.host == host ) {
		member.priority=1;
        member.hidden={{hidden}};
    }
});
rs.reconfig(cfg);
`
