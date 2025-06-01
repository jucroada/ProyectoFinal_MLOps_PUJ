import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://fastapi:8989"

# --- Sidebar: Historial de Modelos ---
st.sidebar.title("Historial de Modelos")
history = requests.get(f"{API_URL}/history").json()
history_df = pd.DataFrame(history)
prod_idx = history_df['promoted'].idxmax()
if prod_idx is not None:
    st.sidebar.write("Modelo en producción:")
    st.sidebar.write(history_df.iloc[prod_idx][['run_id', 'model_version', 'trained_at']])

st.sidebar.write("Todos los modelos:")
st.sidebar.dataframe(history_df[['run_id', 'model_version', 'new_r2', 'promoted', 'trained_at']])

# --- Main: Inferencia ---
st.title("Inferencia del precio de vivienda")

with st.form("prediction_form"):
    st.subheader("Ingresa los datos de la vivienda")
    # Puedes personalizar estos campos según las features requeridas
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
        resp = requests.post(f"{API_URL}/predict", json={"features": features})
        if resp.status_code == 200:
            result = resp.json()
            st.success(f"Precio predicho: ${result['prediction']:.2f}")
            st.info(f"Modelo: {result['run_id']} | Versión: {result['model_version']}")
        else:
            st.error(f"Error en predicción: {resp.text}")

# --- Interpretabilidad (SHAP) ---
st.header("Interpretabilidad del modelo (SHAP)")
selected_run = st.selectbox("Selecciona un modelo para analizar SHAP", history_df['run_id'])
if selected_run:
    shap_resp = requests.get(f"{API_URL}/shap/{selected_run}")
    if shap_resp.status_code == 200:
        shap_data = shap_resp.json()['shap_values']
        shap_df = pd.DataFrame.from_dict(shap_data)
        # Mostrar importancias promedio absolutas
        mean_abs = shap_df.abs().mean().sort_values(ascending=False)
        st.subheader("Importancia media absoluta por feature")
        st.bar_chart(mean_abs)
        # Mostrar gráfica interactiva con Plotly (opcional)
        st.subheader("Distribución SHAP por feature")
        st.write(px.box(shap_df, points="all"))
    else:
        st.warning(f"No se encontró SHAP para run_id={selected_run}")

