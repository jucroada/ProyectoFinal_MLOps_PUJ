import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import shap
import io
import os

API_URL = os.getenv("API_URL")

st.set_page_config(page_title="MLOps Real Estate", layout="wide")

# --- SIDEBAR Mejorada ---
st.sidebar.image("https://img.icons8.com/ios-filled/100/real-estate.png", width=60)
st.sidebar.title("MLOps Real Estate")
st.sidebar.markdown(
    """
    **Navegación rápida**
    - Inferencia de precios
    - Historial de modelos
    - Interpretabilidad SHAP

    **¿Cómo funciona?**
    1. Cada vez que se reciben nuevos datos, se entrena un nuevo modelo.
    2. Si el nuevo modelo es mejor, se promueve automáticamente a producción.
    3. Sólo el modelo más reciente promovido está "en producción".
    4. Puedes comparar el desempeño de cada modelo, ver su importancia de variables y realizar inferencias.

    ---
    [Guía rápida](https://github.com/jucroada/ProyectoFinal_MLOps_PUJ)  
    [Contacto Soporte](mailto:jcesarroa@javeriana.edu.co)  
    """
)
st.sidebar.info("Selecciona una pestaña en la parte superior para explorar la app. ¿Dudas? Consulta la ayuda arriba.")

@st.cache_data(ttl=300)
def get_history():
    try:
        r = requests.get(f"{API_URL}/history", timeout=30)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        return pd.DataFrame()

history_df = get_history()
# Determinar el modelo en producción actual (el último promovido)
prod_row = None
if not history_df.empty and "promoted" in history_df.columns:
    prod_rows = history_df[history_df['promoted'] == True]
    if not prod_rows.empty:
        prod_row = prod_rows.iloc[0]
        # Solo el más reciente promovido está "en producción"
        prod_run_id = prod_row["run_id"]
        history_df["currently_in_prod"] = history_df["run_id"] == prod_run_id
    else:
        history_df["currently_in_prod"] = False

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["Inferencia", "Historial de Modelos", "Interpretabilidad (SHAP)"])

# --- 1. INFERENCIA ---
with tab1:
    st.title("Inferencia del precio de vivienda")
    st.markdown("Introduce los datos y consulta el precio estimado usando el **modelo más reciente en producción**.")
    if prod_row is not None:
        st.info(f"**Modelo en producción:**\n\n- Run Name: `{prod_row['run_name']}`\n- ID del modelo: `{prod_row['run_id']}`\n- Versión: `{prod_row['model_version']}`")
    else:
        st.warning("No hay modelo en producción actualmente.")

    with st.form("prediction_form"):
        st.subheader("Ingresa los datos de la vivienda")
        brokered_by = st.number_input("Agencia (brokered_by)", min_value=0, max_value=20)
        status      = st.selectbox("Status", ["ready to build", "ready to sale"])
        bed         = st.number_input("Habitaciones", min_value=0, max_value=10)
        bath        = st.number_input("Baños", min_value=0, max_value=10)
        acre_lot    = st.number_input("Tamaño lote (acres)", min_value=0.0, step=0.01)
        street      = st.text_input("Calle")
        city        = st.text_input("Ciudad")
        state       = st.text_input("Estado")
        zip_code    = st.text_input("Código postal")
        house_size  = st.number_input("Tamaño casa (pies²)", min_value=0)
        prev_sold_date = st.date_input("Fecha de venta anterior")
        submitted = st.form_submit_button("Predecir precio")

    if submitted:
        features = {
            "brokered_by": brokered_by,
            "status": status,
            "bed": bed,
            "bath": bath,
            "acre_lot": acre_lot,
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "house_size": house_size,
            "prev_sold_date": prev_sold_date.isoformat(),
        }
        try:
            resp = requests.post(f"{API_URL}/predict", json={"features": features}, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                st.success(f"Precio predicho: ${result['prediction']:.2f}")
                # Mostrar run_name y run_id
                run_row = history_df[history_df['run_id'] == result['run_id']].iloc[0] if not history_df.empty else None
                st.info(f"Modelo usado:\n\n- Run Name: `{run_row['run_name']}`\n- ID del modelo: `{result['run_id']}`\n- Versión: `{result['model_version']}`" if run_row is not None else f"Run ID: `{result['run_id']}`")
            else:
                st.error(f"Error en predicción: {resp.text}")
        except Exception as e:
            st.error(f"Error conectando con la API: {e}")

# --- 2. HISTORIAL DE MODELOS ---
with tab2:
    st.header("Historial de Modelos Entrenados")
    st.markdown(
        """
        - **new_\***: Métricas del modelo nuevo sobre el split de test más reciente.
        - **prod_\***: Métricas del modelo anterior en producción sobre el mismo split de test.
        - ⭐ = Actualmente en producción
        - Recuerda: ¡Sólo el último modelo promovido está realmente "en producción"!
        Nota: La métrica para promover un modelo es el MAE en este caso.
        """
    )
    if not history_df.empty:
        prod_filter = st.selectbox("¿Mostrar solo modelos alguna vez promovidos?", ["Todos", "Sí", "No"])
        filtered_df = history_df.copy()
        if prod_filter == "Sí":
            filtered_df = filtered_df[filtered_df['promoted'] == True]
        elif prod_filter == "No":
            filtered_df = filtered_df[filtered_df['promoted'] == False]

        show_df = filtered_df[
            [
                'model_version', 'run_id', 'run_name', 'trained_at', 'promoted', 'currently_in_prod',
                'new_r2', 'prod_r2', 'new_mae', 'prod_mae', 'new_rmse', 'prod_rmse', 'new_mse', 'prod_mse'
            ]
        ].copy()
        show_df = show_df.rename(columns={
            "model_version": "Versión",
            "run_id": "ID del modelo",
            "run_name": "Run Name",
            "trained_at": "Fecha entrenamiento",
            "promoted": "¿Fue promovido?",
            "currently_in_prod": "¿Actualmente en producción?",
            "new_r2": "Nuevo R2",
            "prod_r2": "Prod R2",
            "new_mae": "Nuevo MAE",
            "prod_mae": "Prod MAE",
            "new_rmse": "Nuevo RMSE",
            "prod_rmse": "Prod RMSE",
            "new_mse": "Nuevo MSE",
            "prod_mse": "Prod MSE",
        })

        def prod_icon(row):
            # El único "en producción" es el último promovido
            if row["¿Actualmente en producción?"]:
                return "⭐"
            elif row["¿Fue promovido?"]:
                return "✅"
            else:
                return "—"
        show_df["Estado producción"] = show_df.apply(prod_icon, axis=1)

        # Reordenar columnas para mejor claridad
        cols_order = ["Versión", "Run Name", "ID del modelo", "Fecha entrenamiento", "Estado producción",
                      "Nuevo R2", "Prod R2", "Nuevo MAE", "Prod MAE", "Nuevo RMSE", "Prod RMSE", "Nuevo MSE", "Prod MSE"]
        show_df = show_df[cols_order]

        st.dataframe(show_df.style.hide(axis="index"), use_container_width=True)

        st.markdown("**Comparativa de desempeño entre modelos**")
        if prod_row is not None:
            st.info(
                f"Actualmente en producción:\n\n"
                f"- Run Name: `{prod_row['run_name']}`\n"
                f"- ID del modelo: `{prod_row['run_id']}`\n"
                f"- Versión: `{prod_row['model_version']}`\n"
                f"- Fecha: {prod_row['trained_at']}\n\n"
                f"R2: {prod_row['new_r2']:.4f} | MAE: {prod_row['new_mae']:.2f} | RMSE: {prod_row['new_rmse']:.2f} | MSE: {prod_row['new_mse']:.2f}"
            )
        else:
            st.warning("Ningún modelo está en producción actualmente.")
    else:
        st.warning("No hay historial de modelos registrado.")

# --- 3. INTERPRETABILIDAD (SHAP) ---
with tab3:
    st.header("Interpretabilidad del modelo (SHAP)")
    st.markdown(
        """
        Puedes explorar los valores SHAP para **cualquier modelo**, haya estado o no en producción.
        - Selecciona el modelo de interés para visualizar la importancia de variables.
        - Si el modelo nunca fue promovido, igual puedes consultar su explicabilidad.
        Para mayor información puedes consultar con [docs SHAP](https://shap.readthedocs.io/en/latest/example_notebooks/overviews/An%20introduction%20to%20explainable%20AI%20with%20Shapley%20values.html) 
        """
    )
    if not history_df.empty:
        shap_df_for_select = history_df.copy()
        shap_df_for_select["desc"] = shap_df_for_select.apply(
            lambda r: f"Versión: {r['model_version']} | Run Name: {r['run_name']} | ID: {r['run_id']} | {'⭐ Producción' if r['currently_in_prod'] else 'No producción'}", axis=1
        )
        idx_selected = st.selectbox(
            "Selecciona el modelo para visualizar SHAP",
            shap_df_for_select.index,
            format_func=lambda i: shap_df_for_select.loc[i, "desc"]
        )
        selected_run = shap_df_for_select.loc[idx_selected, "run_id"]
        try:
            shap_resp = requests.get(f"{API_URL}/shap/{selected_run}", timeout=60)
            if shap_resp.status_code == 200:
                shap_data = shap_resp.json()['shap_values']
                shap_df = pd.DataFrame.from_dict(shap_data)

                st.markdown("#### Importancia media absoluta de cada variable")
                mean_abs = shap_df.abs().mean().sort_values(ascending=False)
                st.bar_chart(mean_abs)
                st.dataframe(mean_abs.to_frame("Importancia SHAP").head(10))

                st.markdown("#### Summary Plot de SHAP (beeswarm)")
                with st.spinner("Generando summary plot..."):
                    sample = shap_df
                    if len(shap_df) > 1000:
                        sample = shap_df.sample(1000, random_state=42)
                    plt.figure(figsize=(10,6))
                    shap.summary_plot(sample.values, features=sample.columns, show=False)
                    buf = io.BytesIO()
                    plt.savefig(buf, format="png", bbox_inches='tight')
                    plt.close()
                    st.image(buf.getvalue(), caption="SHAP summary plot (beeswarm)", use_container_width=True)

                st.markdown("#### Boxplot interactivo de SHAP para muestra aleatoria")
                if len(shap_df) > 1000:
                    sample = shap_df.sample(500, random_state=42)
                else:
                    sample = shap_df
                st.write(px.box(sample, points="outliers", title="Distribución SHAP (muestra aleatoria)"))

            else:
                st.warning(f"No se encontró SHAP para run_id={selected_run}")
        except Exception as e:
            st.error(f"Error consultando SHAP: {e}")
    else:
        st.warning("Carga primero el historial de modelos.")

