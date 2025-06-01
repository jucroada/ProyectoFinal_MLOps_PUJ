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
prod_row = history_df.loc[history_df['promoted'] == True].head(1) if not history_df.empty else pd.DataFrame()

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["Inferencia", "Historial de Modelos", "Interpretabilidad (SHAP)"])

# --- 1. INFERENCIA ---
with tab1:
    st.title("Inferencia del precio de vivienda")
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
                st.info(f"Modelo: {result['run_id']} | Versión: {result['model_version']}")
            else:
                st.error(f"Error en predicción: {resp.text}")
        except Exception as e:
            st.error(f"Error conectando con la API: {e}")

# --- 2. HISTORIAL DE MODELOS ---
with tab2:
    st.header("Historial de Modelos Entrenados")
    if not history_df.empty:
        with st.expander("Filtros avanzados"):
            col1, col2 = st.columns(2)
            # Versión de modelo
            min_v, max_v = int(history_df['model_version'].min()), int(history_df['model_version'].max())
            if min_v < max_v:
                ver_range = col1.slider(
                    "Versión de modelo",
                    min_value=min_v,
                    max_value=max_v,
                    value=(min_v, max_v)
                )
            else:
                ver_range = (min_v, max_v)
                col1.number_input("Versión de modelo (solo una)", value=min_v, disabled=True)
            # Producción
            prod_filter = col2.selectbox("¿Mostrar solo modelos en producción?", ["Todos", "Sí", "No"])

        # Aplica los filtros (sin fecha)
        filtered_df = history_df.copy()
        # Versión
        filtered_df = filtered_df[
            (filtered_df['model_version'] >= ver_range[0]) &
            (filtered_df['model_version'] <= ver_range[1])
        ]
        # Producción
        if prod_filter == "Sí":
            filtered_df = filtered_df[filtered_df['promoted'] == True]
        elif prod_filter == "No":
            filtered_df = filtered_df[filtered_df['promoted'] == False]

        # Sólo mostrar los estadísticos de ajuste NEW, y campos relevantes
        show_df = filtered_df[
            [
                'model_version', 'run_id', 'trained_at',
                'promoted', 'new_r2', 'new_mae', 'new_rmse', 'new_mse'
            ]
        ].copy()
        show_df = show_df.rename(columns={
            "model_version": "Versión",
            "run_id": "Run ID",
            "trained_at": "Fecha entrenamiento",
            "promoted": "¿Producción?",
            "new_r2": "R2",
            "new_mae": "MAE",
            "new_rmse": "RMSE",
            "new_mse": "MSE"
        })

        # Mostrar Sí/No+emoji en ¿Producción?
        show_df["¿Producción?"] = show_df["¿Producción?"].map(lambda x: "⭐ Sí" if x else "No")

        # Formatear fecha
        show_df["Fecha entrenamiento"] = pd.to_datetime(show_df["Fecha entrenamiento"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Formato de columnas numéricas
        format_dict = {"R2": "{:.4f}", "MAE": "{:,.2f}", "RMSE": "{:,.2f}", "MSE": "{:,.2f}"}

        # Resaltar toda la fila en negrita si es de producción
        def bold_prod(row):
            return ['font-weight: bold' if row["¿Producción?"].startswith("⭐") else '' for _ in row]

        try:
            styled_df = (
                show_df.style
                .format(format_dict)
                .apply(bold_prod, axis=1)
                .hide(axis="index")
            )
        except Exception:
            styled_df = (
                show_df.style
                .format(format_dict)
                .apply(bold_prod, axis=1)
            )

        st.dataframe(
            styled_df,
            use_container_width=True
        )

        st.markdown("**Modelo actualmente en producción:**")
        if not prod_row.empty:
            st.info(
                f"Versión: {prod_row.iloc[0]['model_version']} | Run_id: {prod_row.iloc[0]['run_id']} | "
                f"Fecha: {prod_row.iloc[0]['trained_at']}\n\n"
                f"R2: {prod_row.iloc[0]['new_r2']:.4f} | MAE: {prod_row.iloc[0]['new_mae']:.2f} | RMSE: {prod_row.iloc[0]['new_rmse']:.2f} | MSE: {prod_row.iloc[0]['new_mse']:.2f}"
            )
        else:
            st.warning("Ningún modelo marcado como producción actualmente.")
    else:
        st.warning("No hay historial de modelos registrado.")

# --- 3. INTERPRETABILIDAD (SHAP) ---
with tab3:
    st.header("Interpretabilidad del modelo (SHAP)")
    if not history_df.empty:
        selected_run = st.selectbox(
            "Selecciona un modelo para analizar SHAP",
            history_df['run_id'],
            format_func=lambda run: f"Run: {run} (Versión: {history_df.set_index('run_id').loc[run]['model_version']})"
        )
        if selected_run:
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

# --- Sidebar: Branding y ayuda ---
st.sidebar.title("Opciones")
st.sidebar.info("Selecciona una pestaña arriba para usar la app.\n\nSi tienes problemas con la visualización de SHAP, intenta con un modelo diferente o refresca la página.")
