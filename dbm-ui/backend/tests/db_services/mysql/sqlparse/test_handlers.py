# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import pytest

from backend.db_services.mysql.sqlparse.exceptions import SQLParseBaseException
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler


class TestSQLParseHandler:
    @staticmethod
    def test_select_for_update():
        sql = "select * from goods where id = 1 and name='prod11' for update;"
        result = SQLParseHandler().parse_sql(sql)
        assert result == {
            "command": "SELECT,UPDATE",
            "query_string": "select * from goods where id = 1 and name='prod11' for update;",
            "query_digest_text": "select * from goods where id = ? and name = '?' for update ;",
            "query_digest_md5": "cd85202ea8e7e56979472302581b9fa9",
            "table_name": "goods",
            "query_length": 62,
        }

    @staticmethod
    def test_include_punctuation():
        sql = """
        select id,'18;19',age,33454354.453 from actor where
        id='dsadsadsadsadsadsadsadsadads'
        and id2=12321321321
        and dt='2011-10-10';
        """
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select id,'18;19',age,33454354.453 from actor where id='dsadsadsadsadsadsadsadsadads' "
            "and id2=12321321321 and dt='2011-10-10';",
            "query_digest_text": "select id , '?' , age , ? from actor where id = '?' and id2 = ? and dt = '?' ;",
            "query_digest_md5": "49ff4686038156fb7dea8b5b2fe59ce5",
            "table_name": "actor",
            "query_length": 128,
        }

    @staticmethod
    def test_join():
        sql = (
            "select trx_state,p.command,p.state, p.user, max(TIMESTAMPDIFF(SECOND,trx_started,now())) "
            "max_trx_long_time, max(p.time) max_trx_idle_time from  information_schema.innodb_trx t join "
            "information_schema.processlist p on t.trx_mysql_thread_id=p.id group by trx_state,command,state,user;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select trx_state,p.command,p.state, p.user, max(TIMESTAMPDIFF(SECOND,trx_started,now()))"
            " max_trx_long_time, max(p.time) max_trx_idle_time from information_schema.innodb_trx t "
            "join information_schema.processlist p on t.trx_mysql_thread_id=p.id group by trx_state,"
            "command,state,user;",
            "query_digest_text": "select trx_state , p . command , p . state , p . user ,"
            " max ( TIMESTAMPDIFF ( SECOND , trx_started , now ( ) ) ) max_trx_long_time , "
            "max ( p . time ) max_trx_idle_time from information_schema . innodb_trx t "
            "join information_schema . processlist p on t . trx_mysql_thread_id = p . id "
            "group by trx_state , command , state , user ;",
            "query_digest_md5": "3d1ebf49578c16081fb1563874177290",
            "table_name": "information_schema.innodb_trx,information_schema.processlist",
            "query_length": 281,
        }

    @staticmethod
    def test_count():
        sql = (
            "select count(*) from  information_schema.INNODB_TRX where  TIMESTAMPDIFF(SECOND,trx_started,now()) > 30;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select count(*) from information_schema.INNODB_TRX "
            "where TIMESTAMPDIFF(SECOND,trx_started,now()) > 30;",
            "query_digest_text": "select count ( * ) from information_schema . INNODB_TRX "
            "where TIMESTAMPDIFF ( SECOND , trx_started , now ( ) ) > ? ;",
            "query_digest_md5": "69302d896e1df76238f89e0b2dede003",
            "table_name": "information_schema.INNODB_TRX",
            "query_length": 102,
        }

    @staticmethod
    def test_rename_two_table():
        sql = (
            "select a.ip, b.port from db_meta_machine a, db_meta_storageinstance b "
            "where a.cluster_type='tendbha' and a.access_layer='storage' and a.bk_host_id = b.machine_id;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select a.ip, b.port from db_meta_machine a, db_meta_storageinstance b where "
            "a.cluster_type='tendbha' and a.access_layer='storage' and a.bk_host_id = b.machine_id;",
            "query_digest_text": "select a . ip , b . port from db_meta_machine a , db_meta_storageinstance b "
            "where a . cluster_type = '?' and a . access_layer = '?' "
            "and a . bk_host_id = b . machine_id ;",
            "query_digest_md5": "60e7cb8bf7ed12639d66a79d8fadff96",
            "table_name": "db_meta_machine,db_meta_storageinstance",
            "query_length": 162,
        }

    @staticmethod
    def test_alert_table():
        sql = "alter table ha_agent_logs add index idx1(agent_ip, ip, port), drop index idx_ins;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "ALTER,DROP",
            "query_string": "alter table ha_agent_logs add index idx1(agent_ip, ip, port), drop index idx_ins;",
            "query_digest_text": "alter table ha_agent_logs add index idx1 ( agent_ip , ip , port ) , "
            "drop index idx_ins ;",
            "query_digest_md5": "c8ce8c74903d0bd2d723e9cc73f0a364",
            "table_name": "ha_agent_logs",
            "query_length": 81,
        }

    @staticmethod
    def test_create_table():
        sql = "create table tb_instance_version_charset(version text, charset int, engines text);"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "CREATE",
            "query_string": "create table tb_instance_version_charset(version text, charset int, engines text);",
            "query_digest_text": "create table tb_instance_version_charset "
            "( version text , charset int , engines text ) ;",
            "query_digest_md5": "52668e3967eb9ae57d845f97381b0440",
            "table_name": "tb_instance_version_charset",
            "query_length": 82,
        }

    @staticmethod
    def test_drop_table():
        sql = "DROP TABLE tb_instance_version_charset;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "DROP",
            "query_string": "DROP TABLE tb_instance_version_charset;",
            "query_digest_text": "DROP TABLE tb_instance_version_charset ;",
            "query_digest_md5": "50ba8416364a3a8df59ec446820649bf",
            "table_name": "tb_instance_version_charset",
            "query_length": 39,
        }

    @staticmethod
    def test_truncate_table():
        sql = "TRUNCATE TABLE tb_instance_version_charset;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "TRUNCATE",
            "query_string": "TRUNCATE TABLE tb_instance_version_charset;",
            "query_digest_text": "TRUNCATE TABLE tb_instance_version_charset ;",
            "query_digest_md5": "421438b35cfc17475a7857b6427e9fd1",
            "table_name": "tb_instance_version_charset",
            "query_length": 43,
        }

    @staticmethod
    def test_insert_into():
        sql = """
         insert into tb_instance_version_charset(ip, port, version, charset, engines, addr, create_at)
          values('127.0.0.1', 20003, '5.5.24-tmysql-1.6-log', 'utf8mb4', 'InnoDB', '127.0.0.1:20003', now());
         """
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "INSERT",
            "query_string": "insert into tb_instance_version_charset(ip, port, version, charset, engines, addr, "
            "create_at) values('127.0.0.1', 20003, '5.5.24-tmysql-1.6-log', 'utf8mb4', 'InnoDB', "
            "'127.0.0.1:20003', now());",
            "query_digest_text": "insert into tb_instance_version_charset ( ip , port , version , charset , engines , "
            "addr , create_at ) values ( '?' , ? , '?' , '?' , '?' , '?' , now ( ) ) ;",
            "query_digest_md5": "6525fca29f39de6e2f7847e6558d9e27",
            "table_name": "tb_instance_version_charset",
            "query_length": 195,
        }

    @staticmethod
    def test_insert_into_with_select():
        # TODO，此 case table name 不对
        sql = """
        INSERT IGNORE INTO gameai_llm_proxy.request_tokens (request_id, create_time)
        SELECT request_id, create_time
        FROM gameai_llm_proxy.request_data;
        """
        print(SQLParseHandler().parse_sql(sql))
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "INSERT,SELECT",
            "query_string": "INSERT IGNORE INTO gameai_llm_proxy.request_tokens (request_id, create_time) "
            "SELECT request_id, create_time FROM gameai_llm_proxy.request_data;",
            "query_digest_text": "INSERT IGNORE INTO gameai_llm_proxy . request_tokens ( request_id , create_time ) "
            "SELECT request_id , create_time FROM gameai_llm_proxy . request_data ;",
            "query_digest_md5": "640fe92d547930b1e7869f514aacd9e3",
            "table_name": "create_time,gameai_llm_proxy.request_data,gameai_llm_proxy.request_tokens,request_id",
            "query_length": 145,
        }

    @staticmethod
    def test_update_data():
        sql = "update db_meta_storageinstance set status='unavailable' where id in (16184,16183);"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "UPDATE",
            "query_string": "update db_meta_storageinstance set status='unavailable' where id in (16184,16183);",
            "query_digest_text": "update db_meta_storageinstance set status = '?' where id in ( ? , ? ) ;",
            "query_digest_md5": "ca4129d268538e8bd332d6898eca0788",
            "table_name": "db_meta_storageinstance",
            "query_length": 82,
        }

    @staticmethod
    def test_complex_sql():
        sql = """
     SELECT --Locais Disponíveis para Abertura de Ordens de corte
     COALESCE(a."Chave", b."Chave") AS "Chave",
     COALESCE(a."Unidade", b."Unidade") AS "Unidade",
     COALESCE(a."Fazenda", b."Fazenda") AS "Fazenda",
     COALESCE(a."Talhao", b."Talhao") AS "Talhao",
     COALESCE(a."Participacao", b."Participacao") AS "Participacao",
     CASE
       WHEN a."Condicao" = 'Disponível Parcial (Moagem)' AND
            b."Condicao" = 'Disponível Parcial (Mudas)' THEN
        'Disponível (Safra+Mudas)'
       ELSE
        COALESCE(a."Condicao", b."Condicao")
     END AS "Condicao",
     COALESCE(a."Estagio", b."Estagio") AS "Estagio",
     COALESCE(a."Variedade", b."Variedade") AS "Variedade",
     COALESCE(a."Ciclo Maturacao", b."Ciclo Maturacao") AS "Ciclo Maturacao",
     COALESCE(a."Propriedade", b."Propriedade") AS "Propriedade",
     COALESCE(a."Proprietario", b."Proprietario") AS "Proprietario",
     COALESCE(a."No. Corte", b."No. Corte") AS "No. Corte",
     (CASE
       WHEN a."Area" IS NULL THEN
    0
       ELSE
        a."Area"
     END + CASE
       WHEN b."Area" IS NULL THEN
    0
       ELSE
        b."Area"
     END) AS "Area",
     CASE
       WHEN a."Condicao" = 'Disponível Parcial (Moagem)' AND
            b."Condicao" = 'Disponível Parcial (Mudas)' THEN
        ((CASE
          WHEN a."Area" IS NULL THEN
    0
          ELSE
           a."Area"
        END + CASE
          WHEN b."Area" IS NULL THEN
    0
          ELSE
           b."Area"
        END) * a."TCH")
       ELSE
        a."Toneladas"
     END AS "Toneladas",
     a."TCH",
     COALESCE(a."Distancia", b."Distancia") AS "Distancia"
      FROM (SELECT --Disponibilidade (Moagem)
             A.*,
             a."Area" * b."TCH" AS "Toneladas",
             b."TCH" AS "TCH",
             c."Dist. Terra" + c."Dist. Asfalto" AS "Distancia"
              FROM ((SELECT --ÁREAS DISPONÍVEIS PARA ABERTURA DE ORDEM CORTE DE SAFRA
                      a."Fazenda" * 1000 + a."Talhao" AS "Chave",
                      CASE
                        WHEN a."Unidade" = 15 THEN
                         'USF'
                        ELSE
                         'URD'
                      END AS "Unidade",
                      a."Fazenda",
                      a."Talhao",
                      a."Participacao",
                      CASE
                        WHEN a."Ocorrencia Cadastro" = 'C' THEN
                         'Disponível Total (Moagem)'
                        ELSE
                         'Disponível Parcial (Moagem)'
                      END AS "Condicao",
                      a."Estagio",
                      a."Variedade",
                      a."Ciclo Maturacao",
                      a."Propriedade",
                      a."Proprietario",
                      a."No. Corte",
                      (a."Area" - (CASE
                        WHEN b."Area Fechada" IS NULL THEN
    0
                        ELSE
                         b."Area Fechada"
                      END)) AS "Area"
                       FROM (SELECT --ULTIMA ESTIMATIVA DO TALHAO A
                              OBJ.CD_UNID_IND AS "Unidade",
                              OBJ.CD_UPNIVEL1 AS "Fazenda",
                              OBJ.CD_UPNIVEL3 AS "Talhao",
                              OBJ.CD_UPNIVEL1 || ' - ' || F.DE_UPNIVEL1 AS "Propriedade",
                              G.DE_FORNEC AS "Proprietario",
                              CASE
                                WHEN UP3.CD_TP_PROPR IN (1, 2, 3, 11) THEN
                                 'Parceria'
                                WHEN UP3.CD_TP_PROPR IN (5, 8) THEN
                                 'Fornecedor'
                                WHEN UP3.CD_TP_PROPR = 6 THEN
                                 'Fornecedor'
                                WHEN UP3.CD_TP_PROPR = 14 THEN
                                 'Parceria'
                                ELSE
                                 'Verificar'
                              END AS "Participacao",
                              C.FG_OCORREN AS "Ocorrencia Cadastro",
                              C.DT_OCORREN AS "Data Ocorrencia",
                              B.DA_ESTAGIO AS "Estagio",
                              B.NO_CORTE AS "No. Corte",
                              D.DE_VARIED AS "Variedade",
                              E.DE_MATURAC AS "Ciclo Maturacao",
                              (OBJ.QT_AREA_PROD * 1) AS "Area",
                              (OBJ.QT_CANA_ENTR / 1000) AS "Toneladas"
                               FROM PIMSCS.HISTPREPRO   OBJ,
                                    PIMSCS.ESTAGIOS     B,
                                    PIMSCS.UPNIVEL3     UP3,
                                    PIMSCS.SAFRUPNIV3   C,
                                    PIMSCS.VARIEDADES   D,
                                    PIMSCS.TIPO_MATURAC E,
                                    PIMSCS.UPNIVEL1     F,
                                    PIMSCS.FORNECS      G
                              WHERE OBJ.CD_SAFRA =
                                    (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                                AND OBJ.CD_UNID_IND IN (15, 19)
                                AND OBJ.CD_ESTAGIO = B.CD_ESTAGIO
                                AND OBJ.CD_UPNIVEL1 = UP3.CD_UPNIVEL1
                                AND OBJ.CD_UPNIVEL3 = UP3.CD_UPNIVEL3
                                AND OBJ.CD_SAFRA = UP3.CD_SAFRA
                                AND OBJ.CD_UPNIVEL1 = C.CD_UPNIVEL1
                                AND OBJ.CD_UPNIVEL3 = C.CD_UPNIVEL3
                                AND OBJ.CD_SAFRA = C.CD_SAFRA
                                AND UP3.CD_VARIED = D.CD_VARIED
                                AND E.FG_MATURAC = D.FG_MATURAC
                                AND OBJ.CD_UPNIVEL1 = F.CD_UPNIVEL1
                                AND F.CD_FORNEC = G.CD_FORNEC
                                AND C.DT_OCORREN =
                                    (SELECT MAX(D.DT_OCORREN)
                                       FROM PIMSCS.SAFRUPNIV3 D
                                      WHERE D.CD_UPNIVEL1 = C.CD_UPNIVEL1
                                        AND D.CD_UPNIVEL3 = C.CD_UPNIVEL3
                                        AND D.CD_SAFRA = C.CD_SAFRA)
                                AND OBJ.CD_HIST =
                                    (SELECT OBJ2.CD_HIST
                                       FROM PIMSCS.HISTPREPRO OBJ2
                                      WHERE OBJ2.CD_UPNIVEL1 = OBJ.CD_UPNIVEL1
                                        AND OBJ2.CD_UPNIVEL3 = OBJ.CD_UPNIVEL3
                                        AND OBJ2.CD_SAFRA =
                                            (SELECT MAX(CD_SAFRA)
                                               FROM PIMSCS.HISTPREPRO)
                                        AND OBJ2.CD_HIST NOT IN ('E', 'S')
                                        AND OBJ2.CD_EMPRESA IN (15, 19)
                                        AND OBJ2.DT_HISTORICO =
                                            (SELECT MAX(OBJ3.DT_HISTORICO)
                                               FROM PIMSCS.HISTPREPRO OBJ3
                                              WHERE OBJ3.CD_UPNIVEL1 =
                                                    OBJ.CD_UPNIVEL1
                                                AND OBJ3.CD_UPNIVEL3 =
                                                    OBJ.CD_UPNIVEL3
                                                AND OBJ3.CD_SAFRA =
                                                    (SELECT MAX(CD_SAFRA)
                                                       FROM PIMSCS.HISTPREPRO)
                                                AND OBJ3.CD_HIST NOT IN ('E', 'S')
                                                AND OBJ3.CD_EMPRESA IN (15, 19)))) A,
                            (SELECT --ÁREA DE ORDEM DE CORTE DE SAFRA FECHADA B
                              QD.CD_UPNIVEL1 AS "Fazenda",
                              QD.CD_UPNIVEL3 AS "Talhao",
                              SUM(QD.QT_AREA) AS "Area Fechada"
                               FROM PIMSCS.QUEIMA_HE QH, PIMSCS.QUEIMA_DE QD
                              WHERE QH.NO_QUEIMA = QD.NO_QUEIMA
                                AND QD.CD_SAFRA =
                                    (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                              GROUP BY QD.CD_UPNIVEL1, QD.CD_UPNIVEL3) B
                      WHERE a."Fazenda" = b."Fazenda"(+)
                        AND a."Talhao" = b."Talhao"(+)
                        AND a."Ocorrencia Cadastro" <> 'F'
                        AND (a."Area" - (CASE
                              WHEN b."Area Fechada" IS NULL THEN
    0
                              ELSE
                               b."Area Fechada"
                            END)) > 0)) A
              LEFT JOIN (SELECT --Ultima Estimativa do Talhão
                         A.CD_HIST "Cod. Historico",
                         CASE
                           WHEN A.CD_UNID_IND = 15 THEN
                            'USF'
                           ELSE
                            'URD'
                         END AS "Unidade",
                         A.CD_UPNIVEL1 AS "Zona",
                         A.CD_UPNIVEL3 AS "Talhao",
                         A.DT_HISTORICO AS "Data",
                         A.QT_AREA_PROD AS "Area",
                         (A.QT_CANA_ENTR / 1000) AS "Toneladas",
                         A.QT_TCH AS "TCH"
                          FROM PIMSCS.HISTPREPRO A
                         WHERE A.CD_UNID_IND IN (15, 19)
                           AND A.CD_SAFRA =
                               (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                           AND A.CD_HIST NOT IN ('E', 'S')
                           AND A.QT_AREA_PROD <> 0
                           AND A.DT_HISTORICO =
                               (SELECT MAX(A2.DT_HISTORICO)
                                  FROM PIMSCS.HISTPREPRO A2
                                 WHERE A.CD_SAFRA = A2.CD_SAFRA
                                   AND A.CD_UPNIVEL2 = A2.CD_UPNIVEL1
                                   AND A.CD_UPNIVEL3 = A2.CD_UPNIVEL3
                                   AND A2.CD_HIST NOT IN ('E', 'S'))) B
                ON a."Fazenda" = b."Zona"
               AND a."Talhao" = b."Talhao"
              LEFT JOIN (SELECT --Distancia Cadastrada
                         A.CD_UPNIVEL1 AS "Zona",
                         A.CD_UPNIVEL3 AS "Talhao",
                         MAX(A.DS_TERRA) AS "Dist. Terra",
                         MAX(A.DS_ASFALTO) AS "Dist. Asfalto"
                          FROM PIMSCS.UPNIVEL3 A
                          LEFT JOIN PIMSCS.SAFRUPNIV3 B
                            ON A.CD_SAFRA = B.CD_SAFRA
                           AND A.CD_UPNIVEL1 = B.CD_UPNIVEL1
                           AND A.CD_UPNIVEL3 = B.CD_UPNIVEL3
                         WHERE A.CD_UNID_IND IN (15, 19)
                           AND A.CD_OCUP = 1
                           AND A.CD_SAFRA =
                               (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                           AND B.CD_SAFRA =
                               (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                           AND B.FG_OCORREN <> 'I'
                           AND B.DT_OCORREN =
                               (SELECT MAX(B2.DT_OCORREN)
                                  FROM PIMSCS.SAFRUPNIV3 B2
                                 WHERE B.CD_SAFRA = B2.CD_SAFRA
                                   AND B.CD_UPNIVEL1 = B2.CD_UPNIVEL1
                                   AND B.CD_UPNIVEL3 = B2.CD_UPNIVEL3)
                         GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) C
                ON a."Fazenda" = c."Zona"
               AND a."Talhao" = c."Talhao") A
      FULL JOIN (SELECT --Disponibilidade (Mudas)
                  A.*,
                  a."Area" * b."TCH" AS "Toneladas",
                  b."TCH" AS "TCH",
                  c."Dist. Terra" + c."Dist. Asfalto" AS "Distancia"
                   FROM ((SELECT --ÁREAS DISPONÍVEIS PARA ABERTURA DE ORDEM CORTE DE SAFRA
                           a."Fazenda" * 1000 + a."Talhao" AS "Chave",
                           CASE
                             WHEN a."Unidade" = 15 THEN
                              'USF'
                             ELSE
                              'URD'
                           END AS "Unidade",
                           a."Fazenda",
                           a."Talhao",
                           a."Participacao",
                           CASE
                             WHEN a."Ocorrencia Cadastro" = 'C' THEN
                              'Disponível Total (Mudas)'
                             ELSE
                              'Disponível Parcial (Mudas)'
                           END AS "Condicao",
                           a."Estagio",
                           a."Variedade",
                           a."Ciclo Maturacao",
                           a."Propriedade",
                           a."Proprietario",
                           a."No. Corte",
                           (a."Area" - (CASE
                             WHEN b."Area Fechada" IS NULL THEN
    0
                             ELSE
                              b."Area Fechada"
                           END)) AS "Area"
                            FROM (SELECT --ULTIMA ESTIMATIVA DO TALHAO A
                                   OBJ.CD_UNID_IND AS "Unidade",
                                   OBJ.CD_UPNIVEL1 AS "Fazenda",
                                   OBJ.CD_UPNIVEL3 AS "Talhao",
                                   OBJ.CD_UPNIVEL1 || ' - ' || F.DE_UPNIVEL1 AS "Propriedade",
                                   G.DE_FORNEC AS "Proprietario",
                                   CASE
                                     WHEN UP3.CD_TP_PROPR IN (1, 2, 3, 11) THEN
                                      'Parceria'
                                     WHEN UP3.CD_TP_PROPR IN (5, 8) THEN
                                      'Fornecedor'
                                     WHEN UP3.CD_TP_PROPR = 6 THEN
                                      'Fornecedor'
                                     WHEN UP3.CD_TP_PROPR = 14 THEN
                                      'Parceria'
                                     ELSE
                                      'Verificar'
                                   END AS "Participacao",
                                   C.FG_OCORREN AS "Ocorrencia Cadastro",
                                   C.DT_OCORREN AS "Data Ocorrencia",
                                   B.DA_ESTAGIO AS "Estagio",
                                   B.NO_CORTE AS "No. Corte",
                                   D.DE_VARIED AS "Variedade",
                                   E.DE_MATURAC AS "Ciclo Maturacao",
                                   (OBJ.QT_AREA_PROD * 1) AS "Area",
                                   (OBJ.QT_CANA_ENTR / 1000) AS "Toneladas"
                                    FROM PIMSCS.HISTPREPRO   OBJ,
                                         PIMSCS.ESTAGIOS     B,
                                         PIMSCS.UPNIVEL3     UP3,
                                         PIMSCS.SAFRUPNIV3   C,
                                         PIMSCS.VARIEDADES   D,
                                         PIMSCS.TIPO_MATURAC E,
                                         PIMSCS.UPNIVEL1     F,
                                         PIMSCS.FORNECS      G
                                   WHERE OBJ.CD_SAFRA =
                                         (SELECT MAX(CD_SAFRA)
                                            FROM PIMSCS.HISTPREPRO)
                                     AND OBJ.CD_UNID_IND IN (15, 19)
                                     AND OBJ.CD_ESTAGIO = B.CD_ESTAGIO
                                     AND OBJ.CD_UPNIVEL1 = UP3.CD_UPNIVEL1
                                     AND OBJ.CD_UPNIVEL3 = UP3.CD_UPNIVEL3
                                     AND OBJ.CD_SAFRA = UP3.CD_SAFRA
                                     AND OBJ.CD_UPNIVEL1 = C.CD_UPNIVEL1
                                     AND OBJ.CD_UPNIVEL3 = C.CD_UPNIVEL3
                                     AND OBJ.CD_SAFRA = C.CD_SAFRA
                                     AND UP3.CD_VARIED = D.CD_VARIED
                                     AND E.FG_MATURAC = D.FG_MATURAC
                                     AND OBJ.CD_UPNIVEL1 = F.CD_UPNIVEL1
                                     AND F.CD_FORNEC = G.CD_FORNEC
                                     AND C.DT_OCORREN =
                                         (SELECT MAX(D.DT_OCORREN)
                                            FROM PIMSCS.SAFRUPNIV3 D
                                           WHERE D.CD_UPNIVEL1 = C.CD_UPNIVEL1
                                             AND D.CD_UPNIVEL3 = C.CD_UPNIVEL3
                                             AND D.CD_SAFRA = C.CD_SAFRA)
                                     AND OBJ.CD_HIST =
                                         (SELECT OBJ2.CD_HIST
                                            FROM PIMSCS.HISTPREPRO OBJ2
                                           WHERE OBJ2.CD_UPNIVEL1 = OBJ.CD_UPNIVEL1
                                             AND OBJ2.CD_UPNIVEL3 = OBJ.CD_UPNIVEL3
                                             AND OBJ2.CD_SAFRA =
                                                 (SELECT MAX(CD_SAFRA)
                                                    FROM PIMSCS.HISTPREPRO)
                                             AND OBJ2.CD_HIST = 'S'
                                             AND OBJ2.CD_EMPRESA IN (15, 19)
                                             AND OBJ2.DT_HISTORICO =
                                                 (SELECT MAX(OBJ3.DT_HISTORICO)
                                                    FROM PIMSCS.HISTPREPRO OBJ3
                                                   WHERE OBJ3.CD_UPNIVEL1 =
                                                         OBJ.CD_UPNIVEL1
                                                     AND OBJ3.CD_UPNIVEL3 =
                                                         OBJ.CD_UPNIVEL3
                                                     AND OBJ3.CD_SAFRA =
                                                         (SELECT MAX(CD_SAFRA)
                                                            FROM PIMSCS.HISTPREPRO)
                                                     AND OBJ3.CD_HIST = 'S'
                                                     AND OBJ3.CD_EMPRESA IN (15, 19)))) A,
                                 (SELECT --ÁREA DE ORDEM DE CORTE DE MUDAS FECHADA B
                                   A.CD_UPNIVEL1 AS "Fazenda",
                                   A.CD_UPNIVEL3 AS "Talhao",
                                   SUM(A.QT_AREA) AS "Area Fechada"
                                    FROM  PIMSCS.OCORTEMD_DE A
                                    JOIN PIMSCS.OCORTEMD_HE B
                                      ON A.NO_ORDEM = B.NO_ORDEM
                                   WHERE A.CD_SAFRA =
                                         (SELECT MAX(CD_SAFRA)
                                            FROM PIMSCS.HISTPREPRO)
                                     AND B.FG_SITUACAO = 'F'
                                   GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) B
                           WHERE a."Fazenda" = b."Fazenda"(+)
                             AND a."Talhao" = b."Talhao"(+)
                             AND a."Ocorrencia Cadastro" <> 'F'
                             AND (a."Area" - (CASE
                                   WHEN b."Area Fechada" IS NULL THEN
    0
                                   ELSE
                                    b."Area Fechada"
                                 END)) > 0)) A
                   LEFT JOIN (SELECT --Ultima Estimativa do Talhão
                              A.CD_HIST "Cod. Historico",
                              CASE
                                WHEN A.CD_UNID_IND = 15 THEN
                                 'USF'
                                ELSE
                                 'URD'
                              END AS "Unidade",
                              A.CD_UPNIVEL1 AS "Zona",
                              A.CD_UPNIVEL3 AS "Talhao",
                              A.DT_HISTORICO AS "Data",
                              A.QT_AREA_PROD AS "Area",
                              (A.QT_CANA_ENTR / 1000) AS "Toneladas",
                              A.QT_TCH AS "TCH"
                               FROM PIMSCS.HISTPREPRO A
                              WHERE A.CD_UNID_IND IN (15, 19)
                                AND A.CD_SAFRA =
                                    (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                                AND A.CD_HIST = 'S'
                                AND A.QT_AREA_PROD <> 0
                                AND A.DT_HISTORICO =
                                    (SELECT MAX(A2.DT_HISTORICO)
                                       FROM PIMSCS.HISTPREPRO A2
                                      WHERE A.CD_SAFRA = A2.CD_SAFRA
                                        AND A.CD_UPNIVEL2 = A2.CD_UPNIVEL1
                                        AND A.CD_UPNIVEL3 = A2.CD_UPNIVEL3
                                        AND A2.CD_HIST = 'S')) B
                     ON a."Fazenda" = b."Zona"
                    AND a."Talhao" = b."Talhao"
                   LEFT JOIN (SELECT --Distancia Cadastrada
                              A.CD_UPNIVEL1 AS "Zona",
                              A.CD_UPNIVEL3 AS "Talhao",
                              MAX(A.DS_TERRA) AS "Dist. Terra",
                              MAX(A.DS_ASFALTO) AS "Dist. Asfalto"
                               FROM PIMSCS.UPNIVEL3 A
                               LEFT JOIN PIMSCS.SAFRUPNIV3 B
                                 ON A.CD_SAFRA = B.CD_SAFRA
                                AND A.CD_UPNIVEL1 = B.CD_UPNIVEL1
                                AND A.CD_UPNIVEL3 = B.CD_UPNIVEL3
                              WHERE A.CD_UNID_IND IN (15, 19)
                                AND A.CD_OCUP = 1
                                AND A.CD_SAFRA =
                                    (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                                AND B.CD_SAFRA =
                                    (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO)
                                AND B.FG_OCORREN <> 'I'
                                AND B.DT_OCORREN =
                                    (SELECT MAX(B2.DT_OCORREN)
                                       FROM PIMSCS.SAFRUPNIV3 B2
                                      WHERE B.CD_SAFRA = B2.CD_SAFRA
                                        AND B.CD_UPNIVEL1 = B2.CD_UPNIVEL1
                                        AND B.CD_UPNIVEL3 = B2.CD_UPNIVEL3)
                              GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) C
                     ON a."Fazenda" = c."Zona"
                    AND a."Talhao" = c."Talhao") B
        ON a."Chave" = b."Chave"

        """
        print(SQLParseHandler().parse_sql(sql))
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": 'SELECT --Locais Disponíveis para Abertura de Ordens de corte COALESCE(a."Chave", '
            'b."Chave") AS "Chave", COALESCE(a."Unidade", b."Unidade") AS "Unidade", '
            'COALESCE(a."Fazenda", b."Fazenda") AS "Fazenda", COALESCE(a."Talhao", b."Talhao") AS '
            '"Talhao", COALESCE(a."Participacao", b."Participacao") AS "Participacao", '
            'CASE WHEN a."Condicao" = \'Disponível Parcial (Moagem)\' AND b."Condicao" = \'Disponível '
            "Parcial (Mudas)' THEN 'Disponível (Safra+Mudas)' ELSE COALESCE(a.\"Condicao\", "
            'b."Condicao") END AS "Condicao", COALESCE(a."Estagio", b."Estagio") AS "Estagio", '
            'COALESCE(a."Variedade", b."Variedade") AS "Variedade", COALESCE(a."Ciclo Maturacao", '
            'b."Ciclo Maturacao") AS "Ciclo Maturacao", COALESCE(a."Propriedade", b."Propriedade") AS '
            '"Propriedade", COALESCE(a."Proprietario", b."Proprietario") AS "Proprietario", '
            'COALESCE(a."No. Corte", b."No. Corte") AS "No. Corte", (CASE WHEN a."Area" IS NULL THEN '
            '0 ELSE a."Area" END + CASE WHEN b."Area" IS NULL THEN 0 ELSE b."Area" END) AS "Area", '
            'CASE WHEN a."Condicao" = \'Disponível Parcial (Moagem)\' AND b."Condicao" = \'Disponível '
            'Parcial (Mudas)\' THEN ((CASE WHEN a."Area" IS NULL THEN 0 ELSE a."Area" END + CASE WHEN '
            'b."Area" IS NULL THEN 0 ELSE b."Area" END) * a."TCH") ELSE a."Toneladas" END AS '
            '"Toneladas", a."TCH", COALESCE(a."Distancia", b."Distancia") AS "Distancia" FROM (SELECT '
            '--Disponibilidade (Moagem) A.*, a."Area" * b."TCH" AS "Toneladas", b."TCH" AS "TCH", '
            'c."Dist. Terra" + c."Dist. Asfalto" AS "Distancia" FROM ((SELECT --ÁREAS DISPONÍVEIS '
            'PARA ABERTURA DE ORDEM CORTE DE SAFRA a."Fazenda" * 1000 + a."Talhao" AS "Chave", '
            'CASE WHEN a."Unidade" = 15 THEN \'USF\' ELSE \'URD\' END AS "Unidade", a."Fazenda", '
            'a."Talhao", a."Participacao", CASE WHEN a."Ocorrencia Cadastro" = \'C\' THEN '
            "'Disponível Total (Moagem)' ELSE 'Disponível Parcial (Moagem)' END AS \"Condicao\", "
            'a."Estagio", a."Variedade", a."Ciclo Maturacao", a."Propriedade", a."Proprietario", '
            'a."No. Corte", (a."Area" - (CASE WHEN b."Area Fechada" IS NULL THEN 0 ELSE b."Area '
            'Fechada" END)) AS "Area" FROM (SELECT --ULTIMA ESTIMATIVA DO TALHAO A OBJ.CD_UNID_IND AS '
            '"Unidade", OBJ.CD_UPNIVEL1 AS "Fazenda", OBJ.CD_UPNIVEL3 AS "Talhao", OBJ.CD_UPNIVEL1 || '
            '\' - \' || F.DE_UPNIVEL1 AS "Propriedade", G.DE_FORNEC AS "Proprietario", '
            "CASE WHEN UP3.CD_TP_PROPR IN (1, 2, 3, 11) THEN 'Parceria' WHEN UP3.CD_TP_PROPR IN (5, "
            "8) THEN 'Fornecedor' WHEN UP3.CD_TP_PROPR = 6 THEN 'Fornecedor' WHEN UP3.CD_TP_PROPR "
            "= 14 THEN 'Parceria' ELSE 'Verificar' END AS \"Participacao\", C.FG_OCORREN AS "
            '"Ocorrencia Cadastro", C.DT_OCORREN AS "Data Ocorrencia", B.DA_ESTAGIO AS "Estagio", '
            'B.NO_CORTE AS "No. Corte", D.DE_VARIED AS "Variedade", E.DE_MATURAC AS "Ciclo '
            'Maturacao", (OBJ.QT_AREA_PROD * 1) AS "Area", (OBJ.QT_CANA_ENTR / 1000) AS "Toneladas" '
            "FROM PIMSCS.HISTPREPRO OBJ, PIMSCS.ESTAGIOS B, PIMSCS.UPNIVEL3 UP3, PIMSCS.SAFRUPNIV3 C, "
            "PIMSCS.VARIEDADES D, PIMSCS.TIPO_MATURAC E, PIMSCS.UPNIVEL1 F, PIMSCS.FORNECS G WHERE "
            "OBJ.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND OBJ.CD_UNID_IND IN (15, "
            "19) AND OBJ.CD_ESTAGIO = B.CD_ESTAGIO AND OBJ.CD_UPNIVEL1 = UP3.CD_UPNIVEL1 AND "
            "OBJ.CD_UPNIVEL3 = UP3.CD_UPNIVEL3 AND OBJ.CD_SAFRA = UP3.CD_SAFRA AND OBJ.CD_UPNIVEL1 = "
            "C.CD_UPNIVEL1 AND OBJ.CD_UPNIVEL3 = C.CD_UPNIVEL3 AND OBJ.CD_SAFRA = C.CD_SAFRA AND "
            "UP3.CD_VARIED = D.CD_VARIED AND E.FG_MATURAC = D.FG_MATURAC AND OBJ.CD_UPNIVEL1 = "
            "F.CD_UPNIVEL1 AND F.CD_FORNEC = G.CD_FORNEC AND C.DT_OCORREN = (SELECT MAX(D.DT_OCORREN) "
            "FROM PIMSCS.SAFRUPNIV3 D WHERE D.CD_UPNIVEL1 = C.CD_UPNIVEL1 AND D.CD_UPNIVEL3 = "
            "C.CD_UPNIVEL3 AND D.CD_SAFRA = C.CD_SAFRA) AND OBJ.CD_HIST = (SELECT OBJ2.CD_HIST FROM "
            "PIMSCS.HISTPREPRO OBJ2 WHERE OBJ2.CD_UPNIVEL1 = OBJ.CD_UPNIVEL1 AND OBJ2.CD_UPNIVEL3 = "
            "OBJ.CD_UPNIVEL3 AND OBJ2.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND "
            "OBJ2.CD_HIST NOT IN ('E', 'S') AND OBJ2.CD_EMPRESA IN (15, 19) AND OBJ2.DT_HISTORICO "
            "= (SELECT MAX(OBJ3.DT_HISTORICO) FROM PIMSCS.HISTPREPRO OBJ3 WHERE OBJ3.CD_UPNIVEL1 = "
            "OBJ.CD_UPNIVEL1 AND OBJ3.CD_UPNIVEL3 = OBJ.CD_UPNIVEL3 AND OBJ3.CD_SAFRA = (SELECT MAX("
            "CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND OBJ3.CD_HIST NOT IN ('E', 'S') AND "
            "OBJ3.CD_EMPRESA IN (15, 19)))) A, (SELECT --ÁREA DE ORDEM DE CORTE DE SAFRA FECHADA B "
            'QD.CD_UPNIVEL1 AS "Fazenda", QD.CD_UPNIVEL3 AS "Talhao", SUM(QD.QT_AREA) AS "Area '
            'Fechada" FROM PIMSCS.QUEIMA_HE QH, PIMSCS.QUEIMA_DE QD WHERE QH.NO_QUEIMA = QD.NO_QUEIMA '
            "AND QD.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) GROUP BY QD.CD_UPNIVEL1, "
            'QD.CD_UPNIVEL3) B WHERE a."Fazenda" = b."Fazenda"(+) AND a."Talhao" = b."Talhao"(+) AND '
            'a."Ocorrencia Cadastro" <> \'F\' AND (a."Area" - (CASE WHEN b."Area Fechada" IS NULL '
            'THEN 0 ELSE b."Area Fechada" END)) > 0)) A LEFT JOIN (SELECT --Ultima Estimativa do '
            "Talhão A.CD_HIST \"Cod. Historico\", CASE WHEN A.CD_UNID_IND = 15 THEN 'USF' ELSE "
            '\'URD\' END AS "Unidade", A.CD_UPNIVEL1 AS "Zona", A.CD_UPNIVEL3 AS "Talhao", '
            'A.DT_HISTORICO AS "Data", A.QT_AREA_PROD AS "Area", (A.QT_CANA_ENTR / 1000) AS '
            '"Toneladas", A.QT_TCH AS "TCH" FROM PIMSCS.HISTPREPRO A WHERE A.CD_UNID_IND IN (15, '
            "19) AND A.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND A.CD_HIST NOT IN "
            "('E', 'S') AND A.QT_AREA_PROD <> 0 AND A.DT_HISTORICO = (SELECT MAX(A2.DT_HISTORICO) "
            "FROM PIMSCS.HISTPREPRO A2 WHERE A.CD_SAFRA = A2.CD_SAFRA AND A.CD_UPNIVEL2 = "
            "A2.CD_UPNIVEL1 AND A.CD_UPNIVEL3 = A2.CD_UPNIVEL3 AND A2.CD_HIST NOT IN ('E', "
            '\'S\'))) B ON a."Fazenda" = b."Zona" AND a."Talhao" = b."Talhao" LEFT JOIN (SELECT '
            '--Distancia Cadastrada A.CD_UPNIVEL1 AS "Zona", A.CD_UPNIVEL3 AS "Talhao", '
            'MAX(A.DS_TERRA) AS "Dist. Terra", MAX(A.DS_ASFALTO) AS "Dist. Asfalto" FROM '
            "PIMSCS.UPNIVEL3 A LEFT JOIN PIMSCS.SAFRUPNIV3 B ON A.CD_SAFRA = B.CD_SAFRA AND "
            "A.CD_UPNIVEL1 = B.CD_UPNIVEL1 AND A.CD_UPNIVEL3 = B.CD_UPNIVEL3 WHERE A.CD_UNID_IND IN ("
            "15, 19) AND A.CD_OCUP = 1 AND A.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) "
            "AND B.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND B.FG_OCORREN <> 'I' "
            "AND B.DT_OCORREN = (SELECT MAX(B2.DT_OCORREN) FROM PIMSCS.SAFRUPNIV3 B2 WHERE B.CD_SAFRA "
            "= B2.CD_SAFRA AND B.CD_UPNIVEL1 = B2.CD_UPNIVEL1 AND B.CD_UPNIVEL3 = B2.CD_UPNIVEL3) "
            'GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) C ON a."Fazenda" = c."Zona" AND a."Talhao" = '
            'c."Talhao") A FULL JOIN (SELECT --Disponibilidade (Mudas) A.*, a."Area" * b."TCH" AS '
            '"Toneladas", b."TCH" AS "TCH", c."Dist. Terra" + c."Dist. Asfalto" AS "Distancia" FROM ('
            '(SELECT --ÁREAS DISPONÍVEIS PARA ABERTURA DE ORDEM CORTE DE SAFRA a."Fazenda" * 1000 + '
            'a."Talhao" AS "Chave", CASE WHEN a."Unidade" = 15 THEN \'USF\' ELSE \'URD\' END AS '
            '"Unidade", a."Fazenda", a."Talhao", a."Participacao", CASE WHEN a."Ocorrencia Cadastro" '
            "= 'C' THEN 'Disponível Total (Mudas)' ELSE 'Disponível Parcial (Mudas)' END AS "
            '"Condicao", a."Estagio", a."Variedade", a."Ciclo Maturacao", a."Propriedade", '
            'a."Proprietario", a."No. Corte", (a."Area" - (CASE WHEN b."Area Fechada" IS NULL THEN 0 '
            'ELSE b."Area Fechada" END)) AS "Area" FROM (SELECT --ULTIMA ESTIMATIVA DO TALHAO A '
            'OBJ.CD_UNID_IND AS "Unidade", OBJ.CD_UPNIVEL1 AS "Fazenda", OBJ.CD_UPNIVEL3 AS "Talhao", '
            "OBJ.CD_UPNIVEL1 || ' - ' || F.DE_UPNIVEL1 AS \"Propriedade\", G.DE_FORNEC AS "
            "\"Proprietario\", CASE WHEN UP3.CD_TP_PROPR IN (1, 2, 3, 11) THEN 'Parceria' WHEN "
            "UP3.CD_TP_PROPR IN (5, 8) THEN 'Fornecedor' WHEN UP3.CD_TP_PROPR = 6 THEN "
            "'Fornecedor' WHEN UP3.CD_TP_PROPR = 14 THEN 'Parceria' ELSE 'Verificar' END AS "
            '"Participacao", C.FG_OCORREN AS "Ocorrencia Cadastro", C.DT_OCORREN AS "Data '
            'Ocorrencia", B.DA_ESTAGIO AS "Estagio", B.NO_CORTE AS "No. Corte", D.DE_VARIED AS '
            '"Variedade", E.DE_MATURAC AS "Ciclo Maturacao", (OBJ.QT_AREA_PROD * 1) AS "Area", '
            '(OBJ.QT_CANA_ENTR / 1000) AS "Toneladas" FROM PIMSCS.HISTPREPRO OBJ, PIMSCS.ESTAGIOS B, '
            "PIMSCS.UPNIVEL3 UP3, PIMSCS.SAFRUPNIV3 C, PIMSCS.VARIEDADES D, PIMSCS.TIPO_MATURAC E, "
            "PIMSCS.UPNIVEL1 F, PIMSCS.FORNECS G WHERE OBJ.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM "
            "PIMSCS.HISTPREPRO) AND OBJ.CD_UNID_IND IN (15, 19) AND OBJ.CD_ESTAGIO = B.CD_ESTAGIO AND "
            "OBJ.CD_UPNIVEL1 = UP3.CD_UPNIVEL1 AND OBJ.CD_UPNIVEL3 = UP3.CD_UPNIVEL3 AND OBJ.CD_SAFRA "
            "= UP3.CD_SAFRA AND OBJ.CD_UPNIVEL1 = C.CD_UPNIVEL1 AND OBJ.CD_UPNIVEL3 = C.CD_UPNIVEL3 "
            "AND OBJ.CD_SAFRA = C.CD_SAFRA AND UP3.CD_VARIED = D.CD_VARIED AND E.FG_MATURAC = "
            "D.FG_MATURAC AND OBJ.CD_UPNIVEL1 = F.CD_UPNIVEL1 AND F.CD_FORNEC = G.CD_FORNEC AND "
            "C.DT_OCORREN = (SELECT MAX(D.DT_OCORREN) FROM PIMSCS.SAFRUPNIV3 D WHERE D.CD_UPNIVEL1 = "
            "C.CD_UPNIVEL1 AND D.CD_UPNIVEL3 = C.CD_UPNIVEL3 AND D.CD_SAFRA = C.CD_SAFRA) AND "
            "OBJ.CD_HIST = (SELECT OBJ2.CD_HIST FROM PIMSCS.HISTPREPRO OBJ2 WHERE OBJ2.CD_UPNIVEL1 = "
            "OBJ.CD_UPNIVEL1 AND OBJ2.CD_UPNIVEL3 = OBJ.CD_UPNIVEL3 AND OBJ2.CD_SAFRA = (SELECT MAX("
            "CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND OBJ2.CD_HIST = 'S' AND OBJ2.CD_EMPRESA IN (15, "
            "19) AND OBJ2.DT_HISTORICO = (SELECT MAX(OBJ3.DT_HISTORICO) FROM PIMSCS.HISTPREPRO OBJ3 "
            "WHERE OBJ3.CD_UPNIVEL1 = OBJ.CD_UPNIVEL1 AND OBJ3.CD_UPNIVEL3 = OBJ.CD_UPNIVEL3 AND "
            "OBJ3.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND OBJ3.CD_HIST = 'S' "
            "AND OBJ3.CD_EMPRESA IN (15, 19)))) A, (SELECT --ÁREA DE ORDEM DE CORTE DE MUDAS FECHADA "
            'B A.CD_UPNIVEL1 AS "Fazenda", A.CD_UPNIVEL3 AS "Talhao", SUM(A.QT_AREA) AS "Area '
            'Fechada" FROM PIMSCS.OCORTEMD_DE A JOIN PIMSCS.OCORTEMD_HE B ON A.NO_ORDEM = B.NO_ORDEM '
            "WHERE A.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND B.FG_SITUACAO = "
            '\'F\' GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) B WHERE a."Fazenda" = b."Fazenda"(+) AND '
            'a."Talhao" = b."Talhao"(+) AND a."Ocorrencia Cadastro" <> \'F\' AND (a."Area" - (CASE '
            'WHEN b."Area Fechada" IS NULL THEN 0 ELSE b."Area Fechada" END)) > 0)) A LEFT JOIN ('
            'SELECT --Ultima Estimativa do Talhão A.CD_HIST "Cod. Historico", CASE WHEN A.CD_UNID_IND '
            "= 15 THEN 'USF' ELSE 'URD' END AS \"Unidade\", A.CD_UPNIVEL1 AS \"Zona\", A.CD_UPNIVEL3 "
            'AS "Talhao", A.DT_HISTORICO AS "Data", A.QT_AREA_PROD AS "Area", (A.QT_CANA_ENTR / 1000) '
            'AS "Toneladas", A.QT_TCH AS "TCH" FROM PIMSCS.HISTPREPRO A WHERE A.CD_UNID_IND IN (15, '
            "19) AND A.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND A.CD_HIST = 'S' "
            "AND A.QT_AREA_PROD <> 0 AND A.DT_HISTORICO = (SELECT MAX(A2.DT_HISTORICO) FROM "
            "PIMSCS.HISTPREPRO A2 WHERE A.CD_SAFRA = A2.CD_SAFRA AND A.CD_UPNIVEL2 = A2.CD_UPNIVEL1 "
            'AND A.CD_UPNIVEL3 = A2.CD_UPNIVEL3 AND A2.CD_HIST = \'S\')) B ON a."Fazenda" = b."Zona" '
            'AND a."Talhao" = b."Talhao" LEFT JOIN (SELECT --Distancia Cadastrada A.CD_UPNIVEL1 AS '
            '"Zona", A.CD_UPNIVEL3 AS "Talhao", MAX(A.DS_TERRA) AS "Dist. Terra", MAX(A.DS_ASFALTO) '
            'AS "Dist. Asfalto" FROM PIMSCS.UPNIVEL3 A LEFT JOIN PIMSCS.SAFRUPNIV3 B ON A.CD_SAFRA = '
            "B.CD_SAFRA AND A.CD_UPNIVEL1 = B.CD_UPNIVEL1 AND A.CD_UPNIVEL3 = B.CD_UPNIVEL3 WHERE "
            "A.CD_UNID_IND IN (15, 19) AND A.CD_OCUP = 1 AND A.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM "
            "PIMSCS.HISTPREPRO) AND B.CD_SAFRA = (SELECT MAX(CD_SAFRA) FROM PIMSCS.HISTPREPRO) AND "
            "B.FG_OCORREN <> 'I' AND B.DT_OCORREN = (SELECT MAX(B2.DT_OCORREN) FROM "
            "PIMSCS.SAFRUPNIV3 B2 WHERE B.CD_SAFRA = B2.CD_SAFRA AND B.CD_UPNIVEL1 = B2.CD_UPNIVEL1 "
            "AND B.CD_UPNIVEL3 = B2.CD_UPNIVEL3) GROUP BY A.CD_UPNIVEL1, A.CD_UPNIVEL3) C ON "
            'a."Fazenda" = c."Zona" AND a."Talhao" = c."Talhao") B ON a."Chave" = b."Chave"',
            # noqa
            "query_digest_text": "SELECT --Locais Disponíveis para Abertura de Ordens de corte COALESCE ( a . '?' , "
            "b . '?' ) AS '?' , COALESCE ( a . '?' , b . '?' ) AS '?' , COALESCE ( a . '?' , "
            "b . '?' ) AS '?' , COALESCE ( a . '?' , b . '?' ) AS '?' , COALESCE ( a . '?' , "
            "b . '?' ) AS '?' , CASE WHEN a . '?' = '?' AND b . '?' = '?' THEN '?' ELSE COALESCE "
            "( a . '?' , b . '?' ) END AS '?' , COALESCE ( a . '?' , b . '?' ) AS '?' , "
            "COALESCE ( a . '?' , b . '?' ) AS '?' , COALESCE ( a . '?' , b . '?' ) AS '?' , "
            "COALESCE ( a . '?' , b . '?' ) AS '?' , COALESCE ( a . '?' , b . '?' ) AS '?' , "
            "COALESCE ( a . '?' , b . '?' ) AS '?' , ( CASE WHEN a . '?' IS NULL THEN ? ELSE a . "
            "'?' END + CASE WHEN b . '?' IS NULL THEN ? ELSE b . '?' END ) AS '?' , CASE WHEN a "
            ". '?' = '?' AND b . '?' = '?' THEN ( ( CASE WHEN a . '?' IS NULL THEN ? ELSE a . "
            "'?' END + CASE WHEN b . '?' IS NULL THEN ? ELSE b . '?' END ) * a . '?' ) ELSE a . "
            "'?' END AS '?' , a . '?' , COALESCE ( a . '?' , b . '?' ) AS '?' FROM ( SELECT "
            "--Disponibilidade (Moagem) A . * , a . '?' * b . '?' AS '?' , b . '?' AS '?' , "
            "c . '?' + c . '?' AS '?' FROM ( ( SELECT --ÁREAS DISPONÍVEIS PARA ABERTURA DE ORDEM "
            "CORTE DE SAFRA a . '?' * ? + a . '?' AS '?' , CASE WHEN a . '?' = ? THEN '?' ELSE "
            "'?' END AS '?' , a . '?' , a . '?' , a . '?' , CASE WHEN a . '?' = '?' THEN '?' "
            "ELSE '?' END AS '?' , a . '?' , a . '?' , a . '?' , a . '?' , a . '?' , a . '?' , "
            "( a . '?' - ( CASE WHEN b . '?' IS NULL THEN ? ELSE b . '?' END ) ) AS '?' FROM ( "
            "SELECT --ULTIMA ESTIMATIVA DO TALHAO A OBJ . CD_UNID_IND AS '?' , OBJ . CD_UPNIVEL1 "
            "AS '?' , OBJ . CD_UPNIVEL3 AS '?' , OBJ . CD_UPNIVEL1 || '?' || F . DE_UPNIVEL1 AS "
            "'?' , G . DE_FORNEC AS '?' , CASE WHEN UP3 . CD_TP_PROPR IN ( ? , ? , ? , "
            "? ) THEN '?' WHEN UP3 . CD_TP_PROPR IN ( ? , ? ) THEN '?' WHEN UP3 . CD_TP_PROPR = "
            "? THEN '?' WHEN UP3 . CD_TP_PROPR = ? THEN '?' ELSE '?' END AS '?' , C . FG_OCORREN "
            "AS '?' , C . DT_OCORREN AS '?' , B . DA_ESTAGIO AS '?' , B . NO_CORTE AS '?' , "
            "D . DE_VARIED AS '?' , E . DE_MATURAC AS '?' , ( OBJ . QT_AREA_PROD * ? ) AS '?' , "
            "( OBJ . QT_CANA_ENTR / ? ) AS '?' FROM PIMSCS . HISTPREPRO OBJ , PIMSCS . ESTAGIOS "
            "B , PIMSCS . UPNIVEL3 UP3 , PIMSCS . SAFRUPNIV3 C , PIMSCS . VARIEDADES D , "
            "PIMSCS . TIPO_MATURAC E , PIMSCS . UPNIVEL1 F , PIMSCS . FORNECS G WHERE OBJ . "
            "CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND OBJ . "
            "CD_UNID_IND IN ( ? , ? ) AND OBJ . CD_ESTAGIO = B . CD_ESTAGIO AND OBJ . "
            "CD_UPNIVEL1 = UP3 . CD_UPNIVEL1 AND OBJ . CD_UPNIVEL3 = UP3 . CD_UPNIVEL3 AND OBJ . "
            "CD_SAFRA = UP3 . CD_SAFRA AND OBJ . CD_UPNIVEL1 = C . CD_UPNIVEL1 AND OBJ . "
            "CD_UPNIVEL3 = C . CD_UPNIVEL3 AND OBJ . CD_SAFRA = C . CD_SAFRA AND UP3 . CD_VARIED "
            "= D . CD_VARIED AND E . FG_MATURAC = D . FG_MATURAC AND OBJ . CD_UPNIVEL1 = F . "
            "CD_UPNIVEL1 AND F . CD_FORNEC = G . CD_FORNEC AND C . DT_OCORREN = ( SELECT MAX ( D "
            ". DT_OCORREN ) FROM PIMSCS . SAFRUPNIV3 D WHERE D . CD_UPNIVEL1 = C . CD_UPNIVEL1 "
            "AND D . CD_UPNIVEL3 = C . CD_UPNIVEL3 AND D . CD_SAFRA = C . CD_SAFRA ) AND OBJ . "
            "CD_HIST = ( SELECT OBJ2 . CD_HIST FROM PIMSCS . HISTPREPRO OBJ2 WHERE OBJ2 . "
            "CD_UPNIVEL1 = OBJ . CD_UPNIVEL1 AND OBJ2 . CD_UPNIVEL3 = OBJ . CD_UPNIVEL3 AND OBJ2 "
            ". CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND OBJ2 . "
            "CD_HIST NOT IN ( '?' , '?' ) AND OBJ2 . CD_EMPRESA IN ( ? , ? ) AND OBJ2 . "
            "DT_HISTORICO = ( SELECT MAX ( OBJ3 . DT_HISTORICO ) FROM PIMSCS . HISTPREPRO OBJ3 "
            "WHERE OBJ3 . CD_UPNIVEL1 = OBJ . CD_UPNIVEL1 AND OBJ3 . CD_UPNIVEL3 = OBJ . "
            "CD_UPNIVEL3 AND OBJ3 . CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . "
            "HISTPREPRO ) AND OBJ3 . CD_HIST NOT IN ( '?' , '?' ) AND OBJ3 . CD_EMPRESA IN ( ? , "
            "? ) ) ) ) A , ( SELECT --ÁREA DE ORDEM DE CORTE DE SAFRA FECHADA B QD . CD_UPNIVEL1 "
            "AS '?' , QD . CD_UPNIVEL3 AS '?' , SUM ( QD . QT_AREA ) AS '?' FROM PIMSCS . "
            "QUEIMA_HE QH , PIMSCS . QUEIMA_DE QD WHERE QH . NO_QUEIMA = QD . NO_QUEIMA AND QD . "
            "CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) GROUP BY QD . "
            "CD_UPNIVEL1 , QD . CD_UPNIVEL3 ) B WHERE a . '?' = b . '?' ( + ) AND a . '?' = b . "
            "'?' ( + ) AND a . '?' <> '?' AND ( a . '?' - ( CASE WHEN b . '?' IS NULL THEN ? "
            "ELSE b . '?' END ) ) > ? ) ) A LEFT JOIN ( SELECT --Ultima Estimativa do Talhão A . "
            "CD_HIST '?' , CASE WHEN A . CD_UNID_IND = ? THEN '?' ELSE '?' END AS '?' , "
            "A . CD_UPNIVEL1 AS '?' , A . CD_UPNIVEL3 AS '?' , A . DT_HISTORICO AS '?' , "
            "A . QT_AREA_PROD AS '?' , ( A . QT_CANA_ENTR / ? ) AS '?' , A . QT_TCH AS '?' FROM "
            "PIMSCS . HISTPREPRO A WHERE A . CD_UNID_IND IN ( ? , ? ) AND A . CD_SAFRA = ( "
            "SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND A . CD_HIST NOT IN ( '?' , "
            "'?' ) AND A . QT_AREA_PROD <> ? AND A . DT_HISTORICO = ( SELECT MAX ( A2 . "
            "DT_HISTORICO ) FROM PIMSCS . HISTPREPRO A2 WHERE A . CD_SAFRA = A2 . CD_SAFRA AND A "
            ". CD_UPNIVEL2 = A2 . CD_UPNIVEL1 AND A . CD_UPNIVEL3 = A2 . CD_UPNIVEL3 AND A2 . "
            "CD_HIST NOT IN ( '?' , '?' ) ) ) B ON a . '?' = b . '?' AND a . '?' = b . '?' LEFT "
            "JOIN ( SELECT --Distancia Cadastrada A . CD_UPNIVEL1 AS '?' , A . CD_UPNIVEL3 AS "
            "'?' , MAX ( A . DS_TERRA ) AS '?' , MAX ( A . DS_ASFALTO ) AS '?' FROM PIMSCS . "
            "UPNIVEL3 A LEFT JOIN PIMSCS . SAFRUPNIV3 B ON A . CD_SAFRA = B . CD_SAFRA AND A . "
            "CD_UPNIVEL1 = B . CD_UPNIVEL1 AND A . CD_UPNIVEL3 = B . CD_UPNIVEL3 WHERE A . "
            "CD_UNID_IND IN ( ? , ? ) AND A . CD_OCUP = ? AND A . CD_SAFRA = ( SELECT MAX ( "
            "CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND B . CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) "
            "FROM PIMSCS . HISTPREPRO ) AND B . FG_OCORREN <> '?' AND B . DT_OCORREN = ( SELECT "
            "MAX ( B2 . DT_OCORREN ) FROM PIMSCS . SAFRUPNIV3 B2 WHERE B . CD_SAFRA = B2 . "
            "CD_SAFRA AND B . CD_UPNIVEL1 = B2 . CD_UPNIVEL1 AND B . CD_UPNIVEL3 = B2 . "
            "CD_UPNIVEL3 ) GROUP BY A . CD_UPNIVEL1 , A . CD_UPNIVEL3 ) C ON a . '?' = c . '?' "
            "AND a . '?' = c . '?' ) A FULL JOIN ( SELECT --Disponibilidade (Mudas) A . * , "
            "a . '?' * b . '?' AS '?' , b . '?' AS '?' , c . '?' + c . '?' AS '?' FROM ( ( "
            "SELECT --ÁREAS DISPONÍVEIS PARA ABERTURA DE ORDEM CORTE DE SAFRA a . '?' * ? + a . "
            "'?' AS '?' , CASE WHEN a . '?' = ? THEN '?' ELSE '?' END AS '?' , a . '?' , "
            "a . '?' , a . '?' , CASE WHEN a . '?' = '?' THEN '?' ELSE '?' END AS '?' , "
            "a . '?' , a . '?' , a . '?' , a . '?' , a . '?' , a . '?' , ( a . '?' - ( CASE WHEN "
            "b . '?' IS NULL THEN ? ELSE b . '?' END ) ) AS '?' FROM ( SELECT --ULTIMA "
            "ESTIMATIVA DO TALHAO A OBJ . CD_UNID_IND AS '?' , OBJ . CD_UPNIVEL1 AS '?' , "
            "OBJ . CD_UPNIVEL3 AS '?' , OBJ . CD_UPNIVEL1 || '?' || F . DE_UPNIVEL1 AS '?' , "
            "G . DE_FORNEC AS '?' , CASE WHEN UP3 . CD_TP_PROPR IN ( ? , ? , ? , ? ) THEN '?' "
            "WHEN UP3 . CD_TP_PROPR IN ( ? , ? ) THEN '?' WHEN UP3 . CD_TP_PROPR = ? THEN '?' "
            "WHEN UP3 . CD_TP_PROPR = ? THEN '?' ELSE '?' END AS '?' , C . FG_OCORREN AS '?' , "
            "C . DT_OCORREN AS '?' , B . DA_ESTAGIO AS '?' , B . NO_CORTE AS '?' , D . DE_VARIED "
            "AS '?' , E . DE_MATURAC AS '?' , ( OBJ . QT_AREA_PROD * ? ) AS '?' , "
            "( OBJ . QT_CANA_ENTR / ? ) AS '?' FROM PIMSCS . HISTPREPRO OBJ , PIMSCS . ESTAGIOS "
            "B , PIMSCS . UPNIVEL3 UP3 , PIMSCS . SAFRUPNIV3 C , PIMSCS . VARIEDADES D , "
            "PIMSCS . TIPO_MATURAC E , PIMSCS . UPNIVEL1 F , PIMSCS . FORNECS G WHERE OBJ . "
            "CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND OBJ . "
            "CD_UNID_IND IN ( ? , ? ) AND OBJ . CD_ESTAGIO = B . CD_ESTAGIO AND OBJ . "
            "CD_UPNIVEL1 = UP3 . CD_UPNIVEL1 AND OBJ . CD_UPNIVEL3 = UP3 . CD_UPNIVEL3 AND OBJ . "
            "CD_SAFRA = UP3 . CD_SAFRA AND OBJ . CD_UPNIVEL1 = C . CD_UPNIVEL1 AND OBJ . "
            "CD_UPNIVEL3 = C . CD_UPNIVEL3 AND OBJ . CD_SAFRA = C . CD_SAFRA AND UP3 . CD_VARIED "
            "= D . CD_VARIED AND E . FG_MATURAC = D . FG_MATURAC AND OBJ . CD_UPNIVEL1 = F . "
            "CD_UPNIVEL1 AND F . CD_FORNEC = G . CD_FORNEC AND C . DT_OCORREN = ( SELECT MAX ( D "
            ". DT_OCORREN ) FROM PIMSCS . SAFRUPNIV3 D WHERE D . CD_UPNIVEL1 = C . CD_UPNIVEL1 "
            "AND D . CD_UPNIVEL3 = C . CD_UPNIVEL3 AND D . CD_SAFRA = C . CD_SAFRA ) AND OBJ . "
            "CD_HIST = ( SELECT OBJ2 . CD_HIST FROM PIMSCS . HISTPREPRO OBJ2 WHERE OBJ2 . "
            "CD_UPNIVEL1 = OBJ . CD_UPNIVEL1 AND OBJ2 . CD_UPNIVEL3 = OBJ . CD_UPNIVEL3 AND OBJ2 "
            ". CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND OBJ2 . "
            "CD_HIST = '?' AND OBJ2 . CD_EMPRESA IN ( ? , ? ) AND OBJ2 . DT_HISTORICO = ( SELECT "
            "MAX ( OBJ3 . DT_HISTORICO ) FROM PIMSCS . HISTPREPRO OBJ3 WHERE OBJ3 . CD_UPNIVEL1 "
            "= OBJ . CD_UPNIVEL1 AND OBJ3 . CD_UPNIVEL3 = OBJ . CD_UPNIVEL3 AND OBJ3 . CD_SAFRA "
            "= ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND OBJ3 . CD_HIST = '?' AND "
            "OBJ3 . CD_EMPRESA IN ( ? , ? ) ) ) ) A , ( SELECT --ÁREA DE ORDEM DE CORTE DE MUDAS "
            "FECHADA B A . CD_UPNIVEL1 AS '?' , A . CD_UPNIVEL3 AS '?' , SUM ( A . QT_AREA ) AS "
            "'?' FROM PIMSCS . OCORTEMD_DE A JOIN PIMSCS . OCORTEMD_HE B ON A . NO_ORDEM = B . "
            "NO_ORDEM WHERE A . CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) "
            "AND B . FG_SITUACAO = '?' GROUP BY A . CD_UPNIVEL1 , A . CD_UPNIVEL3 ) B WHERE a . "
            "'?' = b . '?' ( + ) AND a . '?' = b . '?' ( + ) AND a . '?' <> '?' AND ( a . '?' - "
            "( CASE WHEN b . '?' IS NULL THEN ? ELSE b . '?' END ) ) > ? ) ) A LEFT JOIN ( "
            "SELECT --Ultima Estimativa do Talhão A . CD_HIST '?' , CASE WHEN A . CD_UNID_IND = "
            "? THEN '?' ELSE '?' END AS '?' , A . CD_UPNIVEL1 AS '?' , A . CD_UPNIVEL3 AS '?' , "
            "A . DT_HISTORICO AS '?' , A . QT_AREA_PROD AS '?' , ( A . QT_CANA_ENTR / ? ) AS '?' "
            ", A . QT_TCH AS '?' FROM PIMSCS . HISTPREPRO A WHERE A . CD_UNID_IND IN ( ? , "
            "? ) AND A . CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND A . "
            "CD_HIST = '?' AND A . QT_AREA_PROD <> ? AND A . DT_HISTORICO = ( SELECT MAX ( A2 . "
            "DT_HISTORICO ) FROM PIMSCS . HISTPREPRO A2 WHERE A . CD_SAFRA = A2 . CD_SAFRA AND A "
            ". CD_UPNIVEL2 = A2 . CD_UPNIVEL1 AND A . CD_UPNIVEL3 = A2 . CD_UPNIVEL3 AND A2 . "
            "CD_HIST = '?' ) ) B ON a . '?' = b . '?' AND a . '?' = b . '?' LEFT JOIN ( SELECT "
            "--Distancia Cadastrada A . CD_UPNIVEL1 AS '?' , A . CD_UPNIVEL3 AS '?' , "
            "MAX ( A . DS_TERRA ) AS '?' , MAX ( A . DS_ASFALTO ) AS '?' FROM PIMSCS . UPNIVEL3 "
            "A LEFT JOIN PIMSCS . SAFRUPNIV3 B ON A . CD_SAFRA = B . CD_SAFRA AND A . "
            "CD_UPNIVEL1 = B . CD_UPNIVEL1 AND A . CD_UPNIVEL3 = B . CD_UPNIVEL3 WHERE A . "
            "CD_UNID_IND IN ( ? , ? ) AND A . CD_OCUP = ? AND A . CD_SAFRA = ( SELECT MAX ( "
            "CD_SAFRA ) FROM PIMSCS . HISTPREPRO ) AND B . CD_SAFRA = ( SELECT MAX ( CD_SAFRA ) "
            "FROM PIMSCS . HISTPREPRO ) AND B . FG_OCORREN <> '?' AND B . DT_OCORREN = ( SELECT "
            "MAX ( B2 . DT_OCORREN ) FROM PIMSCS . SAFRUPNIV3 B2 WHERE B . CD_SAFRA = B2 . "
            "CD_SAFRA AND B . CD_UPNIVEL1 = B2 . CD_UPNIVEL1 AND B . CD_UPNIVEL3 = B2 . "
            "CD_UPNIVEL3 ) GROUP BY A . CD_UPNIVEL1 , A . CD_UPNIVEL3 ) C ON a . '?' = c . '?' "
            "AND a . '?' = c . '?' ) B ON a . '?' = b . '?'",
            # noqa
            "query_digest_md5": "d128d643be71089fbe56ac23ed28f44f",
            "table_name": "PIMSCS.ESTAGIOS,PIMSCS.FORNECS,PIMSCS.HISTPREPRO,PIMSCS.OCORTEMD_DE,PIMSCS.OCORTEMD_HE,"
            "PIMSCS.QUEIMA_DE,PIMSCS.QUEIMA_HE,PIMSCS.SAFRUPNIV3,PIMSCS.TIPO_MATURAC,PIMSCS.UPNIVEL1,"
            "PIMSCS.UPNIVEL3,PIMSCS.VARIEDADES",
            # noqa
            "query_length": 11057,
        }

    @staticmethod
    def test_sql_select_stat():
        sql_no_limit = """
        SELECT e.employee_id, e.employee_name,
        (SELECT COUNT(*) FROM projects p WHERE p.employee_id = e.employee_id LIMIT 3) AS project_count, e.salary
        FROM employees e
        WHERE e.department_id IN (SELECT department_id FROM departments LIMIT) ORDER BY project_count DESC
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(sql_no_limit)

        sql_no_select = """
        UPDATE employees e
        SET bonus = CASE
            WHEN e.salary > (SELECT AVG(salary) FROM employees WHERE department_id = e.department_id)
            THEN e.bonus * 1.2
            ELSE e.bonus * 1.1
        END
        WHERE e.employee_id IN (SELECT DISTINCT employee_id FROM projects WHERE project_status = 'completed');
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(sql_no_select)

        correct_select_sql = """
        SELECT e.employee_id, e.employee_name,
        FROM employees e
        WHERE e.department_id NOT IN (1,2,3) ORDER BY project_count LIMIT 10
        """
        assert SQLParseHandler().parse_select_statement(correct_select_sql) is None

        banned_select_sql = """
        SELECT user, host
        FROM mysql.user
        WHERE user in ("admin", "test") LIMIT 10
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(banned_select_sql)

        show_sql = """
        SHOW DATABASES;
        """
        assert SQLParseHandler().parse_select_statement(show_sql) is None

        desc_sql = """
        DESCRIBE TABLE1;
        """
        assert SQLParseHandler().parse_select_statement(desc_sql) is None

        show_var_sql1 = """
        SHOW VARIABLES;
        """
        assert SQLParseHandler().parse_select_statement(show_var_sql1) is None

        show_var_sql2 = """
        SHOW VARIABLES LIKE %x;
        """
        assert SQLParseHandler().parse_select_statement(show_var_sql2) is None

        show_tables_sql = """
        SHOW TABLES FORM DBM;
        """
        assert SQLParseHandler().parse_select_statement(show_tables_sql) is None

        show_processlist_sql = """
        SHOW PROCESSLIST;
        """
        assert SQLParseHandler().parse_select_statement(show_processlist_sql) is None

        show_slave_sql = """
        SHOW SLAVE STATUS;
        """
        assert SQLParseHandler().parse_select_statement(show_slave_sql) is None

        show_create_table_sql = """
        SHOW CREATE TABLE TEST_DB.TEST_TABLE;
        """
        assert SQLParseHandler().parse_select_statement(show_create_table_sql) is None

        show_index_sql = """
        SHOW INDEX FROM TEST_DB.TEST_TABLE;
        """
        assert SQLParseHandler().parse_select_statement(show_index_sql) is None
