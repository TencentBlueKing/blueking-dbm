#!/usr/bin/perl

use FindBin qw($Bin);

use warnings;
use strict;
use Getopt::Long qw(:config posix_default);
use POSIX qw(strftime);
use File::Basename;
use Data::Dumper;
use DBI;


my $backdir= undef;
my $myconf = undef;
my $increment=0;

# this database will not copy from backup to target, so the target instance innodb ibdata1 cannot be copied too
#my @normal_dbs = ("test", "db_infobase");
my @normal_dbs = ("mysql", "test", "performance_schema", "sys", "db_infobase", "infodba_schema");

Getopt::Long::Configure ("bundling_override");
GetOptions(
	'backup-path=s'    => \$backdir,
	'defaults-file=s'  => \$myconf,
    'increment|i!'  => \$increment
)or die "usage: xxx --backup-path={path} --defaults=file={path} [<-i|increment> <fully-backup-file-dir>]";


unless (defined $backdir && defined $myconf){
    die "back-path or defaults-file undefined";
}

die "$backdir is not a dir" unless( -d $backdir);
my $fully_dir=undef;
if($increment){
    die "when enable increment, fully-backup-file-dir is needed!" unless(@ARGV==1);
    die "$ARGV[0] is not a dir" unless(-d $ARGV[0]);
    $fully_dir=$ARGV[0];
}
my $data_dir        = undef;
my $tokudb_data_dir = undef;
my $tokudb_log_dir  = undef;
my $innodb_home_dir = undef;

open( my $my_cnf_fp, "< $myconf" ) or die "$myconf open error" ;
while ( my $line = <$my_cnf_fp> ) {
    chomp $line;
    if ( not defined $data_dir ) {
        if ( $line =~ /\s*datadir\s*=\s*([\S]+)/ ) {
            $data_dir = $1;
            next;
        }
    }
    if ( not defined $tokudb_data_dir ) {
        if ( $line =~ /\s*tokudb_data_dir\s*=\s*([\S]+)/ ) {
            $tokudb_data_dir = $1;
            next;
        }
    }
    if ( not defined $tokudb_log_dir ) {
        if ( $line =~ /\s*tokudb_log_dir\s*=\s*([\S]+)/ ) {
            $tokudb_log_dir = $1;
            next;
        }
    }
    if ( not defined $innodb_home_dir ) {
        if ( $line =~ /\s*innodb_data_home_dir\s*=\s*([\S]+)/ ) {
            $innodb_home_dir = $1;
            next;
        }
    }
}
close($my_cnf_fp);

unless (defined $data_dir &&
        defined $tokudb_data_dir &&
        defined $tokudb_log_dir )
{
    die "some key in $myconf lost";
}

print "copy tokudb_log to $tokudb_log_dir ...\n";
system("ls $backdir/tokudb_log|xargs -I '{}' cp -r $backdir/tokudb_log/{} $tokudb_log_dir") == 0 or die "failed";
if($increment){
    if(!open FILELIST,"<$backdir/tokudb_data/filelist.txt"){
            die "open filelist.txt failed";
    }
    while(<FILELIST>){
        chomp;
        my $file=$_;
        if(-e "$backdir/tokudb_data/$file"){
            $file="$backdir/tokudb_data/$file";
        }else{
            die "can't find $file in both $backdir/tokudb_data and $fully_dir/tokudb_data" unless(-e ($file="$fully_dir/tokudb_data/$file"));
        }
        system("cp $file $tokudb_data_dir") == 0 or die "failed";
    }
}else{
    print "copy tokudb_data to $tokudb_data_dir ...\n";
    eval{system("ls $backdir/tokudb_data |xargs -I '{}' cp -r $backdir/tokudb_data/{} $tokudb_data_dir")}; die $@ if $@;
}
system("ls $backdir/tokudb.*|xargs -I '{}' cp {} $data_dir") == 0 or die "failed";

foreach my $file (glob("$backdir/mysql_data/*/")){
    my $tmp_file=basename($file);
    if(not grep(/$tmp_file/,@normal_dbs) ){
        print "copy mysql_data/ database: $tmp_file\n";
        system("cp -r $file  $data_dir") == 0 or die "failed";
    }
}

# ibdata1: /data1/mysqldata/20000/innodb/data/ibdata1
# innodb_home_dir: /data1/mysqldata/20000/innodb/data
# innodb_data: /data1/mysqldata/20000/innodb
# if innodb/data/ibdata1 not exists, try to copy from backup
my $innodb_data = dirname($innodb_home_dir);
unless (-e "$innodb_home_dir/ibdata1") {
    print "copy innodb_data: from $backdir/innodb_data/* to $innodb_data \n";
    unless (-e "$backdir/innodb_data") {
        die "lost innodb_data $innodb_home_dir/ibdata1";
    }
    mkdir("$innodb_data");
    system("ls $backdir/innodb_data/ |xargs -I '{}' cp -r $backdir/innodb_data/{} $innodb_data") == 0 or die "failed";

    foreach my $file (glob("$backdir/mysql_data/*/")){
        my $tmp_file=basename($file);
        if(grep(/$tmp_file/,@normal_dbs) ){
            print "copy mysql_data/ database: $tmp_file\n";
            system("cp -r $file  $data_dir") == 0 or die "failed";
        }
    }
} else {
    print "no need to copy innodb_data because $innodb_home_dir/ibdata1 already exists\n";
}