import numpy as np
import pandas as pd

def load_instance():
    
    valor_UF = 39587.48   #al momento de hacer los datos este ees el valor de la UF pero, puede cambiar y se espera que cambie

    # --- Conjuntos ---
    ubicaciones = ["Antofagasta","Copiapo", "Taltal", ]
    horas = list(range(24))
    vehiculos = ["Pesado", "Mediano", "Ligero"]
    panel_tipos = ["PV_LFP_550", "PV_Bifacial_680"]
    cargador_tipos = ["DC_150kW", "HPC_350kW"]
    horizonte_dias = 365 * 5  # 5 años en dias 

    
    demanda_diaria = pd.DataFrame(
        {
            "Pesado": [3200, 1100, 4600],
            "Mediano": [1400, 400, 1800],
            "Ligero": [800, 250, 1100],
        },
        index=ubicaciones,
    )

    # Perfil horario 
    demanda_perfil = np.array([
        0.005, 0.004, 0.004, 0.005, 0.015, 0.035, 0.070, 0.090,
        0.100, 0.110, 0.110, 0.095, 0.085, 0.080, 0.070, 0.055,
        0.040, 0.030, 0.020, 0.015, 0.010, 0.007, 0.005, 0.004,
    ])
    demanda_perfil /= demanda_perfil.sum()

    demanda = {
        (i, t, v): float(demanda_diaria.loc[i, v] * demanda_perfil[t])
        for i in ubicaciones
        for v in vehiculos
        for t in horas
    }


    precio_venta = {
        "Pesado": 320 / valor_UF,
        "Mediano": 285 / valor_UF,
        "Ligero": 255 / valor_UF,
    }
    costo_operativo = {
        "Pesado": 45 / valor_UF,
        "Mediano": 38 / valor_UF,
        "Ligero": 32 / valor_UF,
    }

    precio_base_hora = np.array([
        100,100,100,100,110,110,130,130,140,140,140,140,
        140,140,165,165,165,165,165,165,140,120,120,100
    ])
    matriz_prioridad = {"Copiapo": 1, "Taltal": 1.04, "Antofagasta": 1.08}
    matriz_precios = {
        (i, t): float(precio_base_hora[t] * matriz_prioridad[i] / valor_UF)
        for i in ubicaciones
        for t in horas
    }

    
    perfil_solar = np.array([
        0,0,0,0,0.05,0.12,0.28,0.52,0.72,0.86,0.96,1.00,
        0.96,0.88,0.75,0.58,0.38,0.18,0.06,0,0,0,0,0
    ])
    panel_peak_output = {"PV_LFP_550": 0.55, "PV_Bifacial_680": 0.74}
    generacion_solar = {
        (a, t): float(perfil_solar[t] * panel_peak_output[a])
        for a in panel_tipos
        for t in horas
    }


    panel_capacidad = pd.DataFrame(
        {
            "PV_LFP_550": [1600, 900, 2200],
            "PV_Bifacial_680": [1300, 700, 1900],
        },
        index=ubicaciones,
    )
    panel_fijo = pd.DataFrame(
        {
            "PV_LFP_550": [160_000_000 / valor_UF, 85_000_000 / valor_UF, 240_000_000 / valor_UF],
            "PV_Bifacial_680": [185_000_000 / valor_UF, 100_000_000 / valor_UF, 270_000_000 / valor_UF],
        },
        index=ubicaciones,
    )
    panel_capex = {
        "PV_LFP_550": 280_000 / valor_UF,
        "PV_Bifacial_680": 355_000 / valor_UF,
    }
    panel_om = {
        "PV_LFP_550": 14_000 / valor_UF,
        "PV_Bifacial_680": 18_500/ valor_UF,
    }


    cargador_capacidad = pd.DataFrame(
        {
            "DC_150kW": [7, 3, 11],
            "HPC_350kW": [4, 1, 6],
        },
        index=ubicaciones,
    )
    cargador_capex = {
        "DC_150kW": 26_000_000 / valor_UF,
        "HPC_350kW": 47_000_000/ valor_UF,
    }
    cargador_potencia_nominal = {"DC_150kW": 150, "HPC_350kW": 350}
    cargador_potencia = {
        (k, t): cargador_potencia_nominal[k] for k in cargador_tipos for t in horas
    }

  
    penalizacion_base = {
        "Pesado": 420 / valor_UF,
        "Mediano": 340/ valor_UF,
        "Ligero": 290 / valor_UF,
    }
    prioridad_ubicacion = {"Copiapo": 1.00, "Taltal": 1.08, "Antofagasta": 1.15}
    penalizacion = {
        (i, t, v): float(
            penalizacion_base[v] * prioridad_ubicacion[i] * (1 + 0.4 * demanda_perfil[t])
        )
        for i in ubicaciones
        for v in vehiculos
        for t in horas
    }

    
    presupuesto_capex = 1_200_000_000.0 / valor_UF  


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
        "valor_UF": valor_UF,
    }
