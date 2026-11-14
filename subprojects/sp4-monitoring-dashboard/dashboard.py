"""SP4 monitoring and regional charging-cost estimation prototype."""
from datetime import datetime, time
from pathlib import Path
import json
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
from charging import LOCAL_TZ, candidate_starts, demo_forecast, load_ev_data, load_forecast, quote_session

REPO_ROOT = CURRENT_DIR.parent.parent
TARIFF_FILE = CURRENT_DIR / 'assets' / 'regional_tariffs.json'
FORECAST_FILE = REPO_ROOT / 'data/processed/sp1-demand-forecast-v1.csv'
SNAPSHOT_FILE = CURRENT_DIR / 'assets' / 'demo_ev_snapshot.csv'

st.set_page_config(page_title='EV Charging Observatory', page_icon='⚡', layout='wide')
px.defaults.template = 'plotly_white'
st.markdown('''<style>
.stApp {background:#f5f7fb;}
[data-testid="stMetric"] {background:white;border:1px solid #e1e7ef;border-radius:12px;padding:16px;}
[data-testid="stMetricLabel"] {color:#546476;}
[data-testid="stMetricValue"] {color:#173e63;}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] p {font-size:clamp(1.2rem,3vw,2rem) !important;white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] div,[data-testid="stMetricLabel"] p {white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}
.stApp h1,.stApp h2,.stApp h3 {color:#153958 !important;}
.block-container {padding-top:2rem;}
</style>''', unsafe_allow_html=True)
st.title('⚡ EV Charging Observatory')
st.caption('Charging Monitoring and Visualisation · SP4 · Demand shown in the selected timezone · China price planner in CNY')
registry = json.loads(TARIFF_FILE.read_text(encoding='utf-8'))
profiles = registry['profiles']
with st.sidebar:
    st.header('Charging price profile')
    selected = st.selectbox('Region and charging context', range(len(profiles)), format_func=lambda i: profiles[i]['label'])
    profile = profiles[selected]
    st.caption(profile['basis'])
    manual = st.toggle("Use my station's prices", value=profile['hourly_rates'] is None, key=f"manual_{profile['id']}")
    rates = profile['hourly_rates'] or [0.0] * 24
    if manual:
        st.caption('Enter electricity prices only. Add the service fee separately below.')
        flat = st.number_input('Station electricity price (CNY/kWh)', min_value=0.0, max_value=20.0, value=0.0, step=0.01)
        rates = [flat] * 24
        tou = st.checkbox('Enter time-of-use prices')
        if tou:
            edited = st.data_editor(pd.DataFrame({'Hour':range(24), 'Electricity CNY/kWh':rates}), hide_index=True, disabled=['Hour'], column_config={'Electricity CNY/kWh':st.column_config.NumberColumn(min_value=0.0,max_value=20.0,step=0.01)}, key=f"rates_{profile['id']}")
            rates = edited['Electricity CNY/kWh'].tolist()
        confirmed = st.checkbox("I entered the station's applicable prices", value=False)
    else:
        confirmed = profile['hourly_rates'] is not None
    include_service = st.checkbox('Include a known service fee', value=profile['service_fee'] is not None and not manual, key=f"service_{profile['id']}_{manual}")
    service = st.number_input('Service fee (CNY/kWh)', min_value=0.0, max_value=20.0, value=float(profile['service_fee'] or 0.0), step=0.01, disabled=not include_service, key=f"fee_{profile['id']}_{manual}")
    fee = service if include_service else None
    st.caption('No fee entered means electricity-only. Parking, idle fees and discounts are excluded.')
    st.divider()
    st.markdown(f"[View price source]({profile['source_url']})")
    st.caption(f"Source: {profile['source_date']} · Researched: {registry['researched_on']}")
    st.caption("Published references are not live station quotes. Recheck the operator's displayed prices before charging.")

overview, planner, evidence, integration = st.tabs(['Monitoring','Charging cost planner','Regional price evidence','Subsystem integration'])
with overview:
    st.info('DEMO SNAPSHOT · Vehicles are example records, not live charger telemetry. The view reloads the CSV every 15 seconds.')
    @st.fragment(run_every='15s')
    def monitoring():
        now = pd.Timestamp.now(tz=LOCAL_TZ)
        try:
            evs = load_ev_data(SNAPSHOT_FILE)
        except (OSError, ValueError, pd.errors.ParserError) as error:
            st.error(f'Unable to load vehicle snapshot: {error}')
            return
        a,b,c,d = st.columns(4)
        a.metric('Vehicles connected',len(evs))
        b.metric('Charging now',int((evs.Status == 'Charging').sum()))
        c.metric('Snapshot power',f'{evs.Power_kW.sum():.1f} kW')
        d.metric('Average battery SOC',f'{evs.SOC.mean():.1f}%')
        modified = pd.Timestamp(SNAPSHOT_FILE.stat().st_mtime,unit='s',tz='UTC').tz_convert(LOCAL_TZ)
        st.caption(f'View refreshed {now:%Y-%m-%d %H:%M:%S} China time · snapshot modified {modified:%Y-%m-%d %H:%M:%S}')
        left,right = st.columns([2,1])
        colours = {'Charging':'#167eaa','Waiting':'#f4b04e','Complete':'#28a98f','Offline':'#8190a3'}
        with left:
            st.plotly_chart(px.bar(evs,x='EV_ID',y='SOC',color='Status',range_y=[0,100],title='Battery state of charge',labels={'SOC':'State of charge (%)','EV_ID':'Vehicle'},color_discrete_map=colours),width='stretch',theme=None)
        with right:
            st.plotly_chart(px.pie(evs,names='Status',hole=0.65,title='Connection status',color='Status',color_discrete_map=colours),width='stretch',theme=None)
        if confirmed:
            label = 'Estimated cost rate at current tariff' if fee is not None else 'Electricity-only cost rate'
            st.metric(label,f'¥{evs.Power_kW.sum()*(rates[now.hour]+(fee or 0)):.2f}/h')
            st.caption('Power × current unit price. An instantaneous estimate, not an accumulated bill or measured energy.')
        st.dataframe(evs,width='stretch',hide_index=True)
    monitoring()
    st.subheader('Hourly charging demand')
    forecast = None
    demand_timezone = LOCAL_TZ
    if FORECAST_FILE.exists():
        try:
            forecast,metadata = load_forecast(FORECAST_FILE)
            if metadata.get('synthetic'):
                st.warning(f"SYNTHETIC SP1 INPUT · {metadata['source']}")
            else:
                st.success(f"SP1 forecast loaded · {metadata['source']}")
            source_timezone = metadata.get('analysis_timezone', 'UTC')
            try:
                ZoneInfo(source_timezone)
            except (ZoneInfoNotFoundError, TypeError, ValueError):
                source_timezone = 'UTC'
            demand_timezone = st.selectbox('Demand chart timezone',list(dict.fromkeys([source_timezone,'UTC',LOCAL_TZ])),key='sp1_display_timezone')
            forecast = forecast.assign(display_time=forecast.timestamp.dt.tz_convert(demand_timezone))
            st.caption(f"Model: {metadata.get('model', 'not specified')} · {len(forecast):,} hourly intervals · {forecast.display_time.min():%Y-%m-%d %H:%M} to {forecast.display_time.max():%Y-%m-%d %H:%M} ({demand_timezone}).")
            if metadata.get('evaluation_role') == 'historical_rolling_origin_backtest' or forecast.timestamp.max() < pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=2):
                st.info('HISTORICAL SP1 BACKTEST · Predictions for the recorded historical period, not a forecast for today. Vehicle monitoring above still uses fictional example records.')
            st.caption('The demand chart and China charging-price planner use separate inputs. The planner does not calculate costs for this demand series.')
            if metadata.get('interval_method'):
                st.caption('Bounds: '+str(metadata['interval_method']))
            with st.expander('SP1 source, model and validation metadata'):
                st.json(metadata)
            if len(forecast) < 720:
                st.caption('Preview only: fewer than the 30 days specified for the SP2 scheduling interface.')
        except (OSError,ValueError,TypeError,KeyError,pd.errors.ParserError) as error:
            st.error(f'SP1 data rejected: {error}')
    elif st.checkbox('Show synthetic demand example',value=True):
        forecast = demo_forecast(pd.Timestamp.now(tz=LOCAL_TZ).date())
        st.warning("SYNTHETIC EXAMPLE · This curve demonstrates the view; it is not a trained model's prediction.")
    else:
        st.info('SP1 forecast is not yet available. Monitoring and cost estimation remain available.')
    if forecast is not None:
        demand_x = forecast.display_time if 'display_time' in forecast else forecast.local_time
        fig = go.Figure()
        if 'lower_bound_kwh' in forecast and forecast.lower_bound_kwh.notna().any():
            fig.add_trace(go.Scatter(x=demand_x,y=forecast.upper_bound_kwh,mode='lines',line=dict(width=0),showlegend=False))
            fig.add_trace(go.Scatter(x=demand_x,y=forecast.lower_bound_kwh,mode='lines',line=dict(width=0),fill='tonexty',fillcolor='rgba(22,126,170,0.12)',name='SP1 confidence bounds'))
        fig.add_trace(go.Scatter(x=demand_x,y=forecast.predicted_demand_kwh,mode='lines',fill='tozeroy',name='Predicted energy demand',line=dict(color='#167eaa',width=3)))
        fig.update_layout(xaxis_title=f'Time ({demand_timezone})',yaxis_title='Energy per 1-hour interval (kWh)',template='plotly_white',height=330)
        st.plotly_chart(fig,width='stretch',theme=None)
        if FORECAST_FILE.exists():
            st.download_button('Download SP1 forecast CSV',FORECAST_FILE.read_bytes(),file_name=FORECAST_FILE.name,mime='text/csv')
with planner:
    st.subheader('Plan a charging session')
    st.caption('Constant grid-side power estimate. Inputs recalculate immediately; charger limits, battery taper and battery capacity are not modelled.')
    now = pd.Timestamp.now(tz=LOCAL_TZ)
    c1,c2,c3,c4 = st.columns(4)
    session_date = c1.date_input('Charging date',value=now.date())
    start_time = c2.time_input('Arrival / immediate start',value=time(18,0),step=1800)
    power = c3.number_input('Grid charging power (kW)',min_value=0.0,max_value=500.0,value=7.0,step=0.1)
    duration = c4.number_input('Charging duration (hours)',min_value=0.0,max_value=48.0,value=4.0,step=0.25)
    window = st.slider('Vehicle connection window (hours after arrival)',1.0,48.0,max(12.0,duration),step=0.5)
    start = pd.Timestamp(datetime.combine(session_date,start_time),tz=LOCAL_TZ)
    if not confirmed:
        st.info('This region has no verified universal station price. Enter and confirm station prices in the sidebar to calculate.')
    elif duration > window:
        st.error('The charging duration exceeds the available connection window.')
    else:
        try:
            bill = quote_session(start,power,duration,rates,fee)
            options = candidate_starts(start,power,duration,rates,fee,window)
            best = options.loc[options.estimated_subtotal_cny.idxmin()]
            subtotal = float(bill.estimated_subtotal_cny.sum())
            saving = subtotal-float(best.estimated_subtotal_cny)
            a,b,c,d = st.columns(4)
            a.metric('Estimated grid energy',f'{power*duration:.2f} kWh')
            b.metric('Estimated charging subtotal' if fee is not None else 'Electricity-only estimate',f'¥{subtotal:.2f}')
            c.metric('Lowest sampled start cost',f'¥{best.estimated_subtotal_cny:.2f}')
            d.metric('Potential time-shift saving',f'¥{saving:.2f}')
            st.caption(f'Lowest sampled feasible start: {best.start:%Y-%m-%d %H:%M} China time. Compared at 30-minute delays with equal energy and departure deadline. This is a session comparison, not SP2 fleet optimisation.')
            if fee is None:
                st.warning('Service fee is unknown or excluded. The displayed amount is not the full public charging price.')
            if not manual:
                st.info(profile['limitations'])
            x,y = st.columns([2,1])
            with x:
                st.plotly_chart(px.line(options,x='start',y='estimated_subtotal_cny',markers=True,title='Cost for each feasible start',labels={'start':'China local start time','estimated_subtotal_cny':'Estimated subtotal (CNY)'}),width='stretch',theme=None)
            with y:
                split = pd.DataFrame({'Component':['Electricity','Service'],'CNY':[bill.electricity_cost_cny.sum(),bill.service_cost_cny.sum()]})
                st.plotly_chart(px.bar(split,x='Component',y='CNY',color='Component',title='Charging cost breakdown'),width='stretch',theme=None)
            curve = pd.DataFrame({'China local hour':range(24),'Electricity':rates,'Service':[fee or 0]*24})
            st.plotly_chart(px.bar(curve,x='China local hour',y=['Electricity','Service'],title='Daily tariff profile',labels={'value':'CNY per grid kWh','variable':'Component'}),width='stretch',theme=None)
            st.dataframe(bill,width='stretch',hide_index=True)
            st.download_button('Download calculation CSV',bill.to_csv(index=False).encode('utf-8-sig'),file_name='sp4-session-estimate.csv',mime='text/csv')
            assumptions = {'region_profile':profile['id'],'pricing_basis':'User-entered station prices' if manual else profile['basis'],'source_url':None if manual else profile['source_url'],'researched_on':registry['researched_on'],'start_local':start.isoformat(),'power_kw':power,'duration_hours':duration,'hourly_electricity_cny_per_kwh':rates,'service_cny_per_kwh':fee,'excluded':['parking','idle fees','discounts','battery taper'],'not_a_metered_bill':True}
            st.download_button('Download estimate assumptions',json.dumps(assumptions,indent=2).encode(),file_name='sp4-session-estimate.meta.json',mime='application/json')
        except (ValueError,TypeError) as error:
            st.error(f'Cannot calculate this session: {error}')
with evidence:
    st.subheader('Regional charging prices and their evidence')
    st.caption('Research date: '+registry['researched_on']+'. Charging contexts differ; these records are not a city price ranking.')
    rows = []
    for p in profiles:
        numeric = p['hourly_rates']
        rows.append({'Region / context':p['label'],'Electricity CNY/kWh':f'{min(numeric):.4f}–{max(numeric):.4f}' if numeric else 'Station-specific; enter price','Service CNY/kWh':str(p['service_fee']) if p['service_fee'] is not None else 'Unknown / operator-defined','Evidence basis':p['basis'],'Source date':p['source_date'],'Source':p['source_url']})
    st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True,column_config={'Source':st.column_config.LinkColumn('Official source')})
    for p in profiles:
        with st.expander(p['label']):
            st.write(p['limitations'])
            st.markdown(f"[{p['source_title']}]({p['source_url']})")
    st.info('No authenticated operator tariff API is connected. This prototype performs instant calculations against published references or prices you enter; it does not fetch a live national price feed.')
with integration:
    st.subheader('Data readiness')
    files = [('SP1',FORECAST_FILE),('SP2',REPO_ROOT/'data/processed/sp2-charging-schedule-v1.csv'),('SP3',REPO_ROOT/'data/processed/sp3-solar-forecast-v1.csv'),('SP5',REPO_ROOT/'data/processed/sp5-assessment-v1.json')]
    st.dataframe(pd.DataFrame([{'Subsystem':name,'Expected file':path.name,'File present':path.exists(),'Metadata present':path.with_suffix('.meta.json').exists(),'Display integration':'Validated demand chart' if name == 'SP1' else 'Planned; not yet implemented'} for name,path in files]),hide_index=True,width='stretch')
    st.caption('Presence alone does not certify validity. SP1 is validated before display. Other subsystem outputs are planned integration points; no savings or carbon results are invented.')
