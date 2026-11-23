"""Testes unitários para o carregador de quadros de horários no GTFS."""

import io
import unittest
import pandas as pd

from src.gtfs_carregar_qh import (
    BandaHoraria,
    QuadroHorarioCSV,
    aplicar_quadros_gtfs,
    clean_gtfs,
    detectar_alteracoes,
    extrair_service_id_do_nome,
    parse_qh_csv,
    read_gtfs,
    write_gtfs,
)


def criar_gtfs_sintetico() -> dict[str, pd.DataFrame]:
    """Cria um GTFS sintético em memória para testes."""
    routes = pd.DataFrame([
        {"route_id": "R386", "route_short_name": "386", "route_long_name": "Anchieta - Candelária", "route_type": "700"},
        {"route_id": "R817", "route_short_name": "817", "route_long_name": "Piabas - Vargem Grande", "route_type": "700"},
    ])

    trips = pd.DataFrame([
        # Rota 386 - U_REG: Ida (Anchieta) e Volta (Candelária)
        {"route_id": "R386", "service_id": "U_REG", "trip_id": "T386_U_IDA", "trip_headsign": "Anchieta", "direction_id": "0", "shape_id": "S1"},
        {"route_id": "R386", "service_id": "U_REG", "trip_id": "T386_U_VOLTA", "trip_headsign": "Candelária", "direction_id": "1", "shape_id": "S2"},
        # Rota 386 - S_REG: Ida (Anchieta) e Volta (Candelária)
        {"route_id": "R386", "service_id": "S_REG", "trip_id": "T386_S_IDA", "trip_headsign": "Anchieta", "direction_id": "0", "shape_id": "S1"},
        # Rota 817 - U_REG: Circular
        {"route_id": "R817", "service_id": "U_REG", "trip_id": "T817_U_CIRC", "trip_headsign": "Circular", "direction_id": "0", "shape_id": "S3"},
    ])

    stop_times = pd.DataFrame([
        {"trip_id": "T386_U_IDA", "stop_id": "P1", "stop_sequence": "0", "arrival_time": "05:00:00", "departure_time": "05:00:00"},
        {"trip_id": "T386_U_IDA", "stop_id": "P2", "stop_sequence": "1", "arrival_time": "06:00:00", "departure_time": "06:00:00"},
        {"trip_id": "T386_U_VOLTA", "stop_id": "P2", "stop_sequence": "0", "arrival_time": "05:30:00", "departure_time": "05:30:00"},
        {"trip_id": "T386_U_VOLTA", "stop_id": "P1", "stop_sequence": "1", "arrival_time": "06:30:00", "departure_time": "06:30:00"},
        {"trip_id": "T386_S_IDA", "stop_id": "P1", "stop_sequence": "0", "arrival_time": "06:00:00", "departure_time": "06:00:00"},
        {"trip_id": "T386_S_IDA", "stop_id": "P2", "stop_sequence": "1", "arrival_time": "07:00:00", "departure_time": "07:00:00"},
        {"trip_id": "T817_U_CIRC", "stop_id": "P3", "stop_sequence": "0", "arrival_time": "05:00:00", "departure_time": "05:00:00"},
    ])

    frequencies = pd.DataFrame([
        {"trip_id": "T386_U_IDA", "start_time": "05:00:00", "end_time": "12:00:00", "headway_secs": "1800", "exact_times": "0"},
        {"trip_id": "T386_U_IDA", "start_time": "12:00:00", "end_time": "22:00:00", "headway_secs": "2400", "exact_times": "0"},
        {"trip_id": "T386_U_VOLTA", "start_time": "05:30:00", "end_time": "22:00:00", "headway_secs": "1800", "exact_times": "0"},
    ])

    calendar = pd.DataFrame([
        {"service_id": "U_REG", "monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0", "start_date": "20240101", "end_date": "20281231"},
        {"service_id": "S_REG", "monday": "0", "tuesday": "0", "wednesday": "0", "thursday": "0", "friday": "0", "saturday": "1", "sunday": "0", "start_date": "20240101", "end_date": "20281231"},
    ])

    stops = pd.DataFrame([
        {"stop_id": "P1", "stop_name": "Ponto 1", "stop_lat": "-22.9", "stop_lon": "-43.2"},
        {"stop_id": "P2", "stop_name": "Ponto 2", "stop_lat": "-22.8", "stop_lon": "-43.3"},
        {"stop_id": "P3", "stop_name": "Ponto 3", "stop_lat": "-22.7", "stop_lon": "-43.4"},
    ])

    return {
        "routes": routes,
        "trips": trips,
        "stop_times": stop_times,
        "frequencies": frequencies,
        "calendar": calendar,
        "stops": stops,
    }


class TestCarregarQH(unittest.TestCase):

    def test_extrair_service_id_do_nome(self):
        self.assertEqual(extrair_service_id_do_nome("horarios_386_Anchieta_F_REG.csv"), "F_REG")
        self.assertEqual(extrair_service_id_do_nome("horarios_817_Circular_U_REG.csv"), "U_REG")
        self.assertEqual(extrair_service_id_do_nome("horarios_831_Colonia_S_REG.csv"), "S_REG")
        self.assertEqual(extrair_service_id_do_nome("quadro_386_F.csv"), "F")
        self.assertIsNone(extrair_service_id_do_nome("quadro_sem_calendario.csv"))

    def test_parse_qh_csv(self):
        csv_text = (
            "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
            ",Anchieta,386,05:00:00,09:00:00,1200\n"
            ",Anchieta,386,09:00:00,18:00:00,1800\n"
        )
        buf = io.StringIO(csv_text)
        qh = parse_qh_csv(buf, nome_arquivo="horarios_386_Anchieta_F_REG.csv")
        self.assertEqual(qh.servico, "386")
        self.assertEqual(qh.headsign, "Anchieta")
        self.assertEqual(qh.service_id, "F_REG")
        self.assertEqual(len(qh.bandas), 2)
        self.assertEqual(qh.bandas[0].headway_secs, 1200)
        self.assertEqual(qh.total_partidas, 12 + 18)

    def test_substituicao_direta_apenas_no_sentido(self):
        gtfs = criar_gtfs_sintetico()
        # Modificar a Ida de 386 em U_REG com 2 bandas horárias
        csv_text = (
            "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
            ",Anchieta,386,06:00:00,10:00:00,3600\n"
            ",Anchieta,386,10:00:00,18:00:00,1800\n"
        )
        qh = parse_qh_csv(io.StringIO(csv_text), nome_arquivo="horarios_386_Anchieta_U_REG.csv")
        itens = detectar_alteracoes(gtfs, [qh])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].status, "SUBSTITUICAO_DIRETA")

        novo_gtfs, rel = aplicar_quadros_gtfs(gtfs, itens, permitir_clonagem=False)
        freq = novo_gtfs["frequencies"]
        trips = novo_gtfs["trips"]
        st = novo_gtfs["stop_times"]

        # Invariante SMTR/dbt: frequencies.txt DEVE ter trip_id único (1:1 com trips)
        self.assertTrue(freq["trip_id"].is_unique, "frequencies.txt contém trip_id duplicado!")
        self.assertTrue(trips["trip_id"].is_unique, "trips.txt contém trip_id duplicado!")

        # A viagem antiga T386_U_IDA foi substituída por 2 novas trips (uma para cada banda)
        trips_386_ida = trips[(trips["route_id"] == "R386") & (trips["trip_headsign"] == "Anchieta") & (trips["service_id"] == "U_REG")]
        self.assertEqual(len(trips_386_ida), 2)
        novos_tids = trips_386_ida["trip_id"].tolist()
        self.assertNotIn("T386_U_IDA", novos_tids)

        # Frequências vinculadas 1:1
        freq_ida = freq[freq["trip_id"].isin(novos_tids)].sort_values("start_time")
        self.assertEqual(len(freq_ida), 2)
        self.assertEqual(freq_ida.iloc[0]["start_time"], "06:00:00")
        self.assertEqual(freq_ida.iloc[0]["headway_secs"], "3600")
        self.assertEqual(freq_ida.iloc[1]["start_time"], "10:00:00")
        self.assertEqual(freq_ida.iloc[1]["headway_secs"], "1800")

        # Stop times atualizados para cada banda
        for tid, row_f in freq_ida.set_index("trip_id").iterrows():
            st_tid = st[st["trip_id"] == tid].sort_values("stop_sequence")
            self.assertEqual(st_tid.iloc[0]["departure_time"], row_f["start_time"])

        # O sentido oposto (Volta / T386_U_VOLTA) NÃO foi alterado!
        volta_freq = freq[freq["trip_id"] == "T386_U_VOLTA"]
        self.assertEqual(len(volta_freq), 1)
        self.assertEqual(volta_freq.iloc[0]["start_time"], "05:30:00")

    def test_clonagem_sem_permissao_lanca_erro(self):
        gtfs = criar_gtfs_sintetico()
        # Linha 386 não tem viagem em F_REG
        csv_text = (
            "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
            ",Anchieta,386,06:00:00,10:00:00,3600\n"
        )
        qh = parse_qh_csv(io.StringIO(csv_text), nome_arquivo="horarios_386_Anchieta_F_REG.csv")
        itens = detectar_alteracoes(gtfs, [qh])
        self.assertEqual(itens[0].status, "REQUER_CLONAGEM")
        self.assertEqual(itens[0].molde_service_id, "U_REG")

        # Se permitir_clonagem for False, deve lançar PermissionError
        with self.assertRaises(PermissionError):
            aplicar_quadros_gtfs(gtfs, itens, permitir_clonagem=False)

    def test_clonagem_com_permissao_sucesso(self):
        gtfs = criar_gtfs_sintetico()
        csv_text = (
            "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
            ",Anchieta,386,06:00:00,12:00:00,3600\n"
        )
        qh = parse_qh_csv(io.StringIO(csv_text), nome_arquivo="horarios_386_Anchieta_F_REG.csv")
        itens = detectar_alteracoes(gtfs, [qh])

        novo_gtfs, rel = aplicar_quadros_gtfs(gtfs, itens, permitir_clonagem=True)
        self.assertEqual(rel[0]["status"], "SUCESSO")
        self.assertEqual(rel[0]["tipo_operacao"], "CLONAGEM")

        nova_trip_id = rel[0]["trip_id"]
        # Verifica se nova trip foi criada em trips.txt
        trips_f = novo_gtfs["trips"][novo_gtfs["trips"]["service_id"] == "F_REG"]
        self.assertEqual(len(trips_f), 1)
        self.assertEqual(trips_f.iloc[0]["trip_id"], nova_trip_id)

        # Verifica se paradas foram copiadas em stop_times.txt
        st_f = novo_gtfs["stop_times"][novo_gtfs["stop_times"]["trip_id"] == nova_trip_id]
        self.assertEqual(len(st_f), 2)  # P1 e P2

        # Verifica frequências
        freq_f = novo_gtfs["frequencies"][novo_gtfs["frequencies"]["trip_id"] == nova_trip_id]
        self.assertEqual(len(freq_f), 1)
        self.assertEqual(freq_f.iloc[0]["start_time"], "06:00:00")

        # Verifica se calendar.txt ganhou F_REG
        self.assertIn("F_REG", novo_gtfs["calendar"]["service_id"].values)

    def test_write_and_read_gtfs_zip(self):
        gtfs = criar_gtfs_sintetico()
        buf = io.BytesIO()
        write_gtfs(gtfs, buf)
        buf.seek(0)
        reloaded = read_gtfs(buf)
        self.assertIn("routes", reloaded)
        self.assertEqual(len(reloaded["routes"]), 2)
        self.assertEqual(len(reloaded["trips"]), 4)

    def test_cli_integration(self):
        import json
        import subprocess
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_gtfs_zip = tmp_path / "base_gtfs.zip"
            out_gtfs_zip = tmp_path / "out_gtfs.zip"
            csv_dir = tmp_path / "csvs"
            csv_dir.mkdir()

            gtfs = criar_gtfs_sintetico()
            with open(base_gtfs_zip, "wb") as f:
                write_gtfs(gtfs, f)

            csv1 = (
                "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
                ",Anchieta,386,07:00:00,11:00:00,1800\n"
            )
            (csv_dir / "horarios_386_Anchieta_U_REG.csv").write_text(csv1, encoding="utf-8")

            csv2 = (
                "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs\n"
                ",Anchieta,386,06:00:00,10:00:00,2400\n"
            )
            (csv_dir / "horarios_386_Anchieta_F_REG.csv").write_text(csv2, encoding="utf-8")

            cfg = {
                "endereco_gtfs_base": str(base_gtfs_zip),
                "caminho_saida": str(out_gtfs_zip),
                "arquivos_qh": str(csv_dir),
                "permitir_clonagem": True,
            }
            cfg_path = tmp_path / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            res = subprocess.run(
                ["python", "codigos_py/1.5_carregar_qh_no_gtfs.py", "--config", str(cfg_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(res.returncode, 0)
            self.assertTrue(out_gtfs_zip.exists())

            gtfs_out = read_gtfs(str(out_gtfs_zip))
            freq = gtfs_out["frequencies"]
            trips = gtfs_out["trips"]

            # Invariante SMTR / dbt: unicidade estrita de trip_id
            self.assertTrue(freq["trip_id"].is_unique, "frequencies.txt tem trip_ids duplicados!")
            self.assertTrue(trips["trip_id"].is_unique, "trips.txt tem trip_ids duplicados!")

            u_trips = trips[(trips["route_id"] == "R386") & (trips["trip_headsign"] == "Anchieta") & (trips["service_id"] == "U_REG")]
            self.assertEqual(len(u_trips), 1)
            u_tid = u_trips.iloc[0]["trip_id"]
            ida_u = freq[freq["trip_id"] == u_tid]
            self.assertEqual(len(ida_u), 1)
            self.assertEqual(ida_u.iloc[0]["start_time"], "07:00:00")

            f_trips = trips[trips["service_id"] == "F_REG"]
            self.assertEqual(len(f_trips), 1)
            f_tid = f_trips.iloc[0]["trip_id"]
            f_freq = freq[freq["trip_id"] == f_tid]
            self.assertEqual(len(f_freq), 1)
            self.assertEqual(f_freq.iloc[0]["start_time"], "06:00:00")


if __name__ == "__main__":
    unittest.main()
