import pandas as pd
import gurobipy as gp
from gurobipy import GRB

from datos import load_instance


def describe_model(model: gp.Model):
    model.update()
    vars_ = model.getVars()
    vars_total = len(vars_)
    labels_tipo = {
        GRB.BINARY: "binarias",
        GRB.INTEGER: "enteras",
        GRB.CONTINUOUS: "continuas",
    }
    tipos_variables_cantidad = {label: 0 for label in labels_tipo.values()}
    for var in vars_:
        label = labels_tipo.get(var.VType)
        if label:
            tipos_variables_cantidad[label] += 1

    restricciones = model.getConstrs()
    total_restricciones = len(restricciones)
    restricciones_tipos_cantidad: dict[str, int] = {}
    for restriccion in restricciones:
        base_name = restriccion.ConstrName.split("[", 1)[0]
        if base_name:
            restricciones_tipos_cantidad[base_name] = restricciones_tipos_cantidad.get(base_name, 0) + 1

    print("\nEstructura del modelo:\n")
    tipos_variables = " + ".join(
        f"{count} {label}" for label, count in tipos_variables_cantidad.items()
    )
    print(f"Variables totales: {vars_total} = {tipos_variables}\n")

    print("Restricciones totales: {}".format(total_restricciones))
    for name, count in sorted(restricciones_tipos_cantidad.items()):
        print(f"  - {name}: {count}\n")


def build_model(datos: dict):
    ubicaciones = datos["ubicaciones"]
    horas = datos["horas"]
    vehiculos = datos["vehiculos"]
    panel_tipos = datos["panel_tipos"]
    cargador_tipos = datos["cargador_tipos"]

    demanda = datos["demanda"]
    matriz_precios = datos["matriz_precios"]
    generacion_solar = datos["generacion_solar"]
    panel_capacidad = datos["panel_capacidad"]
    panel_fijo = datos["panel_fijo"]
    panel_capex = datos["panel_capex"]
    panel_om = datos["panel_om"]
    cargador_capacidad = datos["cargador_capacidad"]
    cargador_capex = datos["cargador_capex"]
    cargador_potencia = datos["cargador_potencia"]
    precio_venta = datos["precio_venta"]
    costo_operativo = datos["costo_operativo"]
    penalizacion = datos["penalizacion"]
    horizonte_dias = datos["horizonte_dias"]
    presupuesto_capex = datos["presupuesto_capex"]

    model = gp.Model("infraestructura_electrolineras")
    model.Params.OutputFlag = 0

    x = model.addVars(ubicaciones, vtype=GRB.BINARY, name="x")
    y = model.addVars(ubicaciones, panel_tipos, vtype=GRB.BINARY, name="y")
    n = model.addVars(ubicaciones, panel_tipos, vtype=GRB.INTEGER, lb=0, name="n")
    z = model.addVars(ubicaciones, cargador_tipos, vtype=GRB.INTEGER, lb=0, name="z")
    q = model.addVars(ubicaciones, horas, vehiculos, lb=0.0, name="q")
    grid = model.addVars(ubicaciones, horas, lb=0.0, name="grid")

    model.addConstrs(
        (
            q[i, t, v] <= demanda[i, t, v]
            for i in ubicaciones
            for t in horas
            for v in vehiculos
        ),
        name="demanda_maxima",
    )

    model.addConstrs(
        (
            gp.quicksum(q[i, t, v] for v in vehiculos)
            <= gp.quicksum(generacion_solar[a, t] * n[i, a] for a in panel_tipos)
            + grid[i, t]
            for i in ubicaciones
            for t in horas
        ),
        name="balance_energia",
    )

    model.addConstrs(
        (
            gp.quicksum(q[i, t, v] for v in vehiculos)
            <= gp.quicksum(cargador_potencia[k, t] * z[i, k] for k in cargador_tipos)
            for i in ubicaciones
            for t in horas
        ),
        name="cargador_potencia",
    )

    model.addConstrs(
        (
            n[i, a] <= panel_capacidad.loc[i, a] * y[i, a]
            for i in ubicaciones
            for a in panel_tipos
        ),
        name="panel_capacidad",
    )

    model.addConstrs(
        (
            z[i, k] <= cargador_capacidad.loc[i, k] * x[i]
            for i in ubicaciones
            for k in cargador_tipos
        ),
        name="cargador_capacidad",
    )

    capex_expr = gp.quicksum(
        panel_capex[a] * n[i, a] + panel_fijo.loc[i, a] * y[i, a]
        for i in ubicaciones
        for a in panel_tipos
    ) + gp.quicksum(
        cargador_capex[k] * z[i, k]
        for i in ubicaciones
        for k in cargador_tipos
    )
    model.addConstr(capex_expr <= presupuesto_capex, name="presupuesto_capex")

    ingereso_neto = gp.quicksum(
        (precio_venta[v] - costo_operativo[v]) * q[i, t, v]
        for i in ubicaciones
        for t in horas
        for v in vehiculos
    )
    matriz_costos = gp.quicksum(
        matriz_precios[i, t] * grid[i, t]
        for i in ubicaciones
        for t in horas
    )
    panel_cost = gp.quicksum(
        (panel_capex[a] + panel_om[a]) * n[i, a] + panel_fijo.loc[i, a] * y[i, a]
        for i in ubicaciones
        for a in panel_tipos
    )
    charger_cost = gp.quicksum(
        cargador_capex[k] * z[i, k]
        for i in ubicaciones
        for k in cargador_tipos
    )
    penalizacion_cost = gp.quicksum(
        penalizacion[i, t, v] * (demanda[i, t, v] - q[i, t, v])
        for i in ubicaciones
        for t in horas
        for v in vehiculos
    )

    model.setObjective(
        horizonte_dias * (ingereso_neto - matriz_costos - penalizacion_cost)
        - panel_cost
        - charger_cost,
        sense=GRB.MAXIMIZE,
    )

    model._vars = {
        "x": x,
        "y": y,
        "n": n,
        "z": z,
        "q": q,
        "grid": grid,
    }
    return model


def solve_and_report():
    datos = load_instance()
    model = build_model(datos)
    describe_model(model)
    model.optimize()

    status_labels = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status = status_labels.get(model.Status, f"STATUS_{model.Status}")
    print(f"Status del modelo: {status}\n")
    
    print(f"Tiempo de resolución: {model.Runtime:.2f} s\n")
    
    if model.IsMIP:
        print(f"GAP relativo: {model.MIPGap:.3%}\n")

    if model.Status != GRB.OPTIMAL:
        return

    x = model._vars["x"]
    n = model._vars["n"]
    z = model._vars["z"]
    q = model._vars["q"]
    grid = model._vars["grid"]

    ubicaciones = datos["ubicaciones"]
    horas = datos["horas"]
    vehiculos = datos["vehiculos"]
    panel_tipos = datos["panel_tipos"]
    cargador_tipos = datos["cargador_tipos"]
    panel_capex = datos["panel_capex"]
    panel_fijo = datos["panel_fijo"]
    cargador_capex = datos["cargador_capex"]
    presupuesto_capex = datos["presupuesto_capex"]
    penalizacion = datos["penalizacion"]
    demanda = datos["demanda"]
    horizonte_dias = datos["horizonte_dias"]

    valor_objetivo = model.ObjVal
    total_servido = sum(q[i, t, v].X for i in ubicaciones for t in horas for v in vehiculos)
    total_comprado = sum(grid[i, t].X for i in ubicaciones for t in horas)
    capex_gastado = sum(
        panel_capex[a] * n[i, a].X + panel_fijo.loc[i, a] * model._vars["y"][i, a].X
        for i in ubicaciones
        for a in panel_tipos
    ) + sum(
        cargador_capex[k] * z[i, k].X
        for i in ubicaciones
        for k in cargador_tipos
    )
    solar_servido = max(total_servido - total_comprado, 0.0)

    print(f"Utilidad óptima (horizonte {horizonte_dias} días): {valor_objetivo:,.0f} CLP\n")
    print(f"Energía total servida por día: {total_servido:,.1f} kWh\n")
    if total_servido > 0:
        coeficiente_matriz = total_comprado / total_servido
    else:
        coeficiente_matriz = 0.0
    print(
        f"Energía comprada a la red por día: {total_comprado:,.1f} kWh "
        f"({coeficiente_matriz:.1%} de la energía servida)\n"
    )
    print(f"Energía cubierta por generación solar estimada por día: {solar_servido:,.1f} kWh\n")
    print(
        f"Gasto CAPEX / Inversión: {capex_gastado:,.0f} CLP "
        f"({capex_gastado / presupuesto_capex:.1%} del presupuesto)\n"
    )

    ubicaciones_filas = []
    for i in ubicaciones:
        fila = {
            "ubicación": i,
            "Activo": int(round(x[i].X)),
        }
        fila.update({f"Paneles_{a}": int(round(n[i, a].X)) for a in panel_tipos})
        fila.update({f"Cargadores_{k}": int(round(z[i, k].X)) for k in cargador_tipos})
        ubicaciones_filas.append(fila)
    site_df = pd.DataFrame(ubicaciones_filas).set_index("ubicación")
    print("\nDecisiones de inversión por ubicación:")
    print(site_df)

    servido_desgloce = pd.DataFrame(
        {
            v: [sum(q[i, t, v].X for t in horas) for i in ubicaciones]
            for v in vehiculos
        },
        index=ubicaciones,
    )
    servido_desgloce.loc["Total"] = servido_desgloce.sum()
    print("\nEnergía servida por día (kWh) por ubicación y segmento:")
    print(servido_desgloce.round(1))

    demanda_no_satisfecha = pd.DataFrame(
        {
            v: [
                sum(demanda[i, t, v] - q[i, t, v].X for t in horas)
                for i in ubicaciones
            ]
            for v in vehiculos
        },
        index=ubicaciones,
    )
    demanda_no_satisfecha.loc["Total"] = demanda_no_satisfecha.sum()
    print("\nDemanda no satisfecha por día (kWh) por ubicación y segmento:")
    print(demanda_no_satisfecha.round(1))

    penalizacion_total = sum(
        penalizacion[i, t, v] * (demanda[i, t, v] - q[i, t, v].X)
        for i in ubicaciones
        for t in horas
        for v in vehiculos
    )
    print(f"\nCosto de penalización por día: {penalizacion_total:,.0f} CLP")


if __name__ == "__main__":
    solve_and_report()


