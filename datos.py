import numpy as np
import pandas as pd


def load_instance():
    ubicaciones = ["Copiapo", "Chañaral", "Taltal", "Antofagasta"]
    horas = list(range(24))
    vehiculos = ["CargaPesada", "BusesInterurbanos", "LogisticaLigera"]
    panel_tipos = ["PV_LFP_550", "PV_Bifacial_680"]
    cargador_tipos = ["DC_150kW", "HPC_350kW"]
    horizonte_dias = 1#30 #365 * 5  # delta : horizonte económico en días

    demanda_diaria = pd.DataFrame(
        {
            "CargaPesada": [2600, 1900, 2100, 3050],
            "BusesInterurbanos": [1150, 720, 840, 980],
            "LogisticaLigera": [620, 460, 510, 730],
        },
        index=ubicaciones,
    )
    demanda_perfil = np.array(
        [
            0.015,
            0.012,
            0.010,
            0.010,
            0.012,
            0.020,
            0.035,
            0.055,
            0.070,
            0.085,
            0.095,
            0.100,
            0.100,
            0.095,
            0.085,
            0.070,
            0.055,
            0.040,
            0.028,
            0.018,
            0.012,
            0.010,
            0.010,
            0.008,
        ]
    )
    demanda_perfil = demanda_perfil / demanda_perfil.sum()
    demanda = {
        (i, t, v): float(demanda_diaria.loc[i, v] * demanda_perfil[t])
        for i in ubicaciones
        for v in vehiculos
        for t in horas
    }

    precio_venta = {
        "CargaPesada": 320.0,
        "BusesInterurbanos": 285.0,
        "LogisticaLigera": 255.0,
    }
    costo_operativo = {
        "CargaPesada": 45.0,
        "BusesInterurbanos": 38.0,
        "LogisticaLigera": 32.0,
    }

    matriz_base = np.array(
        [
            118,
            115,
            112,
            110,
            108,
            105,
            102,
            98,
            95,
            94,
            92,
            90,
            92,
            95,
            100,
            108,
            120,
            132,
            140,
            148,
            150,
            146,
            135,
            125,
        ]
    )
    matriz_ponderadores = {
        "Copiapo": 1.00,
        "Chañaral": 1.03,
        "Taltal": 1.05,
        "Antofagasta": 1.08,
    }
    matriz_precios = {
        (i, t): float(matriz_base[t] * matriz_ponderadores[i]) for i in ubicaciones for t in horas
    }

    perfil_solar = np.array(
        [
            0.00,
            0.00,
            0.00,
            0.00,
            0.05,
            0.12,
            0.28,
            0.52,
            0.72,
            0.86,
            0.96,
            1.00,
            0.96,
            0.88,
            0.75,
            0.58,
            0.38,
            0.18,
            0.06,
            0.00,
            0.00,
            0.00,
            0.00,
            0.00,
        ]
    )
    panel_peak_output = {
        "PV_LFP_550": 0.55,
        "PV_Bifacial_680": 0.74,
    }
    generacion_solar = {
        (a, t): float(perfil_solar[t] * panel_peak_output[a])
        for a in panel_tipos
        for t in horas
    }

    panel_capacidad = pd.DataFrame(
        {
            "PV_LFP_550": [1800, 1400, 1500, 2100],
            "PV_Bifacial_680": [1500, 1100, 1200, 1800],
        },
        index=ubicaciones,
    )
    panel_fijo = pd.DataFrame(
        {
            "PV_LFP_550": [180_000_000, 145_000_000, 150_000_000, 210_000_000],
            "PV_Bifacial_680": [205_000_000, 165_000_000, 170_000_000, 235_000_000],
        },
        index=ubicaciones,
    )
    panel_capex = {
        "PV_LFP_550": 280_000.0,
        "PV_Bifacial_680": 355_000.0,
    }
    panel_om = {
        "PV_LFP_550": 14_000.0,
        "PV_Bifacial_680": 18_500.0,
    }

    cargador_capacidad = pd.DataFrame(
        {
            "DC_150kW": [8, 6, 7, 10],
            "HPC_350kW": [5, 3, 4, 6],
        },
        index=ubicaciones,
    )
    cargador_capex = {
        "DC_150kW": 26_000_000.0,
        "HPC_350kW": 47_000_000.0,
    }
    cargador_potencia_nominal = {
        "DC_150kW": 150.0,
        "HPC_350kW": 350.0,
    }
    cargador_potencia = {
        (k, t): cargador_potencia_nominal[k] for k in cargador_tipos for t in horas
    }

    penalizacion_base = {
        "CargaPesada": 420.0,
        "BusesInterurbanos": 360.0,
        "LogisticaLigera": 305.0,
    }
    prioridad_ubicacion = {
        "Copiapo": 1.00,
        "Chañaral": 1.05,
        "Taltal": 1.10,
        "Antofagasta": 1.15,
    }
    penalizacion = {
        (i, t, v): float(penalizacion_base[v] * prioridad_ubicacion[i] * (1 + 0.4 * demanda_perfil[t]))
        for i in ubicaciones
        for v in vehiculos
        for t in horas
    }

    presupuesto_capex = 8_200_000_000.0

    demanda_resumen = (
        pd.Series(demanda).groupby(level=[0, 2]).sum().unstack().round(1)
    )
    demanda_resumen.loc["Total"] = demanda_resumen.sum()

    return {
        "ubicaciones": ubicaciones,
        "horas": horas,
        "vehiculos": vehiculos,
        "panel_tipos": panel_tipos,
        "cargador_tipos": cargador_tipos,
        "horizonte_dias": horizonte_dias,
        "demanda": demanda,
        "demanda_diaria": demanda_diaria,
        "demanda_perfil": demanda_perfil,
        "precio_venta": precio_venta,
        "costo_operativo": costo_operativo,
        "matriz_precios": matriz_precios,
        "generacion_solar": generacion_solar,
        "panel_capacidad": panel_capacidad,
        "panel_fijo": panel_fijo,
        "panel_capex": panel_capex,
        "panel_om": panel_om,
        "cargador_capacidad": cargador_capacidad,
        "cargador_capex": cargador_capex,
        "cargador_potencia": cargador_potencia,
        "penalizacion": penalizacion,
        "presupuesto_capex": presupuesto_capex,
        "demanda_resumen": demanda_resumen,
    }
