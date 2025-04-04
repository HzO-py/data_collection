import streamlit as st
import datetime
import time
import pandas as pd
import urllib.parse

# --------------------------------------------------
# 1) Detailed Tasks
# --------------------------------------------------
DETAILED_TASKS = [
    {"name": "Preparation Phase", "duration": 5 * 60},
    {"name": "Seated Rest", "duration": 5 * 60},
    {"name": "Wearable Device Setup", "duration": 5 * 60},
    # Sitting Baseline (6 min total)
    {"name": "Sitting Baseline - BP Measurement at Beginning", "duration": 30},
    {"name": "Sitting Baseline - Baseline Collection 1",       "duration": 135},
    {"name": "Sitting Baseline - BP Measurement at Middle",    "duration": 30},
    {"name": "Sitting Baseline - Baseline Collection 2",       "duration": 135},
    {"name": "Sitting Baseline - BP Measurement at End",       "duration": 30},
    # Standing Baseline (9 min total)
    {"name": "Standing Baseline - Adaptation",                 "duration": 180},
    {"name": "Standing Baseline - BP Measurement 1",           "duration": 30},
    {"name": "Standing Baseline - Baseline Collection",        "duration": 135},
    {"name": "Standing Baseline - BP Measurement 2",           "duration": 30},
    {"name": "Standing Baseline - Baseline Collection",        "duration": 135},
    {"name": "Standing Baseline - BP Measurement 3",           "duration": 30},
    # Breath-Holding: 3 cycles (200s each) -> total 10 min
    {"name": "Breath-Holding Cycle #1", "duration": 200},
    {"name": "Breath-Holding Cycle #2", "duration": 200},
    {"name": "Breath-Holding Cycle #3", "duration": 200},
    # Treadmill Exercise (15 min total)
    {"name": "Treadmill Exercise - Initial HR & BP Measurement", "duration": 30},
    {"name": "Treadmill Exercise - Jogging Phase",               "duration": 630},
    {"name": "Treadmill Exercise - Post-Jogging BP Measurement", "duration": 30},
    {"name": "Treadmill Exercise - Cool Down Phase",             "duration": 180},
    {"name": "Treadmill Exercise - Final Measurement",           "duration": 30},
    # Recovery Phase (10 min total)
    {"name": "Recovery - Baseline Collection Part 1",        "duration": 270},
    {"name": "Recovery - BP Measurement at 5 Minutes",       "duration": 30},
    {"name": "Recovery - Baseline Collection Part 2",        "duration": 270},
    {"name": "Recovery - BP Measurement at 10 Minutes",      "duration": 30},
    {"name": "Conclusion", "duration": 5 * 60},
]

# --------------------------------------------------
# 2) Group Sub-Tasks by Phase
# --------------------------------------------------
PHASE_GROUPS = [
    {"title": "Preparation Phase (5 min)", "subtasks": ["Preparation Phase"]},
    {"title": "Seated Rest (5 min)", "subtasks": ["Seated Rest"]},
    {"title": "Wearable Device Setup (5 min)", "subtasks": ["Wearable Device Setup"]},
    {"title": "Sitting Baseline (6 min)", "subtasks": [
        "Sitting Baseline - BP Measurement at Beginning",
        "Sitting Baseline - Baseline Collection 1",
        "Sitting Baseline - BP Measurement at Middle",
        "Sitting Baseline - Baseline Collection 2",
        "Sitting Baseline - BP Measurement at End"
    ]},
    {"title": "Standing Baseline (9 min)", "subtasks": [
        "Standing Baseline - Adaptation",
        "Standing Baseline - BP Measurement 1",
        "Standing Baseline - Baseline Collection",
        "Standing Baseline - BP Measurement 2",
        "Standing Baseline - Baseline Collection",
        "Standing Baseline - BP Measurement 3"
    ]},
    {"title": "Breath-Holding Task (10 min)", "subtasks": [
        "Breath-Holding Cycle #1",
        "Breath-Holding Cycle #2",
        "Breath-Holding Cycle #3"
    ]},
    {"title": "Treadmill Exercise (15 min)", "subtasks": [
        "Treadmill Exercise - Initial HR & BP Measurement",
        "Treadmill Exercise - Jogging Phase",
        "Treadmill Exercise - Post-Jogging BP Measurement",
        "Treadmill Exercise - Cool Down Phase",
        "Treadmill Exercise - Final Measurement"
    ]},
    {"title": "Recovery Phase (10 min)", "subtasks": [
        "Recovery - Baseline Collection Part 1",
        "Recovery - BP Measurement at 5 Minutes",
        "Recovery - Baseline Collection Part 2",
        "Recovery - BP Measurement at 10 Minutes"
    ]},
    {"title": "Conclusion (5 min)", "subtasks": ["Conclusion"]}
]

# --------------------------------------------------
# 3) Build Schedule Function
# --------------------------------------------------
def build_schedule(start_time: datetime.datetime):
    schedule = []
    cur = start_time
    for t in DETAILED_TASKS:
        end = cur + datetime.timedelta(seconds=t["duration"])
        schedule.append({
            "name": t["name"],
            "duration": t["duration"],
            "planned_start": cur,
            "planned_end": end
        })
        cur = end
    return schedule

# --------------------------------------------------
# 4) Session State Initialization
# --------------------------------------------------
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "fake_start_time" not in st.session_state:
    st.session_state.fake_start_time = datetime.datetime(2100, 1, 1, 0, 0, 0)
if "schedule" not in st.session_state:
    st.session_state.schedule = build_schedule(st.session_state.fake_start_time)
if "paused" not in st.session_state:
    st.session_state.paused = False
if "pause_start_time" not in st.session_state:
    st.session_state.pause_start_time = None
if "confirm_end_task" not in st.session_state:
    st.session_state.confirm_end_task = False
if "downloaded" not in st.session_state:
    st.session_state.downloaded = False

# Initialize user inputs if not set.
if "device" not in st.session_state:
    st.session_state.device = ""
if "note" not in st.session_state:
    st.session_state.note = ""

# Create a placeholder for the confirmation UI.
confirm_placeholder = st.empty()

# --------------------------------------------------
# 5) Utility Functions
# --------------------------------------------------
def format_mm_ss(seconds: float) -> str:
    s = int(seconds)
    m, s = divmod(s, 60)
    return f"{m}m {s}s"

def shift_schedule(start_index: int, delta_seconds: float):
    schedule = st.session_state.schedule
    delta = datetime.timedelta(seconds=delta_seconds)
    for i in range(start_index, len(schedule)):
        schedule[i]["planned_start"] += delta
        schedule[i]["planned_end"]   += delta

def get_current_task_index(now: datetime.datetime) -> int:
    schedule = st.session_state.schedule
    if not schedule or now < schedule[0]["planned_start"]:
        return -1
    for i, t in enumerate(schedule):
        if t["planned_start"] <= now < t["planned_end"]:
            return i
    return len(schedule)

def toggle_pause():
    if not st.session_state.session_started:
        return
    if not st.session_state.paused:
        st.session_state.paused = True
        st.session_state.pause_start_time = datetime.datetime.now()
    else:
        st.session_state.paused = False
        now = datetime.datetime.now()
        pause_duration = (now - st.session_state.pause_start_time).total_seconds()
        st.session_state.pause_start_time = None
        idx = get_current_task_index(now)
        if idx == -1:
            shift_schedule(0, pause_duration)
        elif idx < len(st.session_state.schedule):
            st.session_state.schedule[idx]["planned_end"] += datetime.timedelta(seconds=pause_duration)
            shift_schedule(idx + 1, pause_duration)

def end_current_task_early():
    now = datetime.datetime.now()
    idx = get_current_task_index(now)
    schedule = st.session_state.schedule
    if 0 <= idx < len(schedule):
        task = schedule[idx]
        remain = (task["planned_end"] - now).total_seconds()
        if remain > 0:
            task["planned_end"] = now
            shift_schedule(idx + 1, -remain)

def build_group_mappings(schedule):
    name_to_index = {task["name"]: i for i, task in enumerate(schedule)}
    group_to_indexes = []
    for g_index, group in enumerate(PHASE_GROUPS):
        indexes = []
        for sub_name in group["subtasks"]:
            if sub_name in name_to_index:
                indexes.append(name_to_index[sub_name])
        indexes.sort()
        group_to_indexes.append(indexes)
    subtask_to_group = {}
    for g_index, idx_list in enumerate(group_to_indexes):
        for idx in idx_list:
            subtask_to_group[idx] = g_index
    return group_to_indexes, subtask_to_group

def get_current_phase_index(now: datetime.datetime) -> int:
    idx = get_current_task_index(now)
    schedule = st.session_state.schedule
    if idx == -1 or idx >= len(schedule):
        return -1
    _, subtask_to_group = build_group_mappings(schedule)
    return subtask_to_group.get(idx, -1)

def group_should_expand(g_index, current_phase_index):
    # Expand only the current phase and the next phase.
    if current_phase_index < 0:
        return False
    if current_phase_index >= len(PHASE_GROUPS) - 1:
        return g_index == current_phase_index
    return g_index == current_phase_index or g_index == current_phase_index + 1

# --------------------------------------------------
# 6) Main Layout
# --------------------------------------------------
st.title("data collection")

col_left, col_right = st.columns([2, 3])

with col_left:
    st.header("Current Timeline")
    now = datetime.datetime.now()
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    effective_now = st.session_state.pause_start_time if st.session_state.paused and st.session_state.pause_start_time else now

    # Before starting, show input fields for Device and Session Note.
    if not st.session_state.session_started:
        st.session_state.device = st.text_input("Device", value=st.session_state.device)
        st.session_state.note = st.text_input("Session Note", value=st.session_state.note)
    else:
        st.write(f"Device: **{st.session_state.device}**")
        st.write(f"Session Note: **{st.session_state.note}**")
    
    st.markdown(
        f"**Current Local Time (California):** <span style='font-size:24px;font-weight:bold;'>{now.strftime('%H:%M:%S')}</span>",
        unsafe_allow_html=True
    )
    st.markdown(f"**Current UTC Time:** {utc_now.strftime('%H:%M:%S')}")
    
    if not st.session_state.session_started:
        if st.button("Start Session"):
            if st.session_state.device.strip() == "" or st.session_state.note.strip() == "":
                st.error("Please enter both Device and Session Note before starting.")
            else:
                st.session_state.schedule = build_schedule(datetime.datetime.now())
                st.session_state.session_started = True
                st.rerun()
    else:
        pause_text = "Resume" if st.session_state.paused else "Pause"
        st.button(pause_text, on_click=toggle_pause)
    
    if st.session_state.session_started:
        schedule = st.session_state.schedule
        idx = get_current_task_index(effective_now)
        if idx != -1 and idx < len(schedule):
            task = schedule[idx]
            remain = max(0, (task["planned_end"] - effective_now).total_seconds())
            st.markdown(
                f"**Remaining Time:** <span style='font-size:24px;font-weight:bold;'>{format_mm_ss(remain)}</span>",
                unsafe_allow_html=True
            )
            st.write(f"Ends at: **{task['planned_end'].strftime('%H:%M:%S')}**")
        
        if not st.session_state.paused:
            if not st.session_state.confirm_end_task:
                if st.button("End This Task Early"):
                    st.session_state.confirm_end_task = True
                    st.rerun()
            else:
                with confirm_placeholder.container():
                    st.warning("Are you sure you want to end the current task early?")
                    col1, col2 = st.columns(2)
                    if col1.button("Yes, End It Now"):
                        end_current_task_early()
                        st.session_state.confirm_end_task = False
                        confirm_placeholder.empty()
                        st.rerun()
                    if col2.button("Cancel"):
                        st.session_state.confirm_end_task = False
                        confirm_placeholder.empty()
                        st.rerun()
        else:
            st.info("Cannot end task early while paused.")

with col_right:
    st.header("Detailed Task Timeline")
    schedule = st.session_state.schedule
    current_phase_index = get_current_phase_index(now)
    group_to_indexes, subtask_to_group = build_group_mappings(schedule)
    for g_index, group in enumerate(PHASE_GROUPS):
        expanded = group_should_expand(g_index, current_phase_index)
        # Mark current phase with a red circle.
        phase_label = group["title"]
        if g_index == current_phase_index:
            phase_label = "🔴 " + phase_label
        with st.expander(phase_label, expanded=expanded):
            for sub_name in group["subtasks"]:
                found = [i for i, t in enumerate(schedule) if t["name"] == sub_name]
                if not found:
                    continue
                i = found[0]
                task = schedule[i]
                start_str = task["planned_start"].strftime("%H:%M:%S")
                end_str = task["planned_end"].strftime("%H:%M:%S")
                if now < task["planned_start"]:
                    st.markdown(f"⏳ **{task['name']}** | Start: {start_str} (Pending)")
                elif task["planned_start"] <= now < task["planned_end"]:
                    st.markdown(
                        f"⏩ <span style='color:red'><strong>{task['name']}</strong></span> | Start: {start_str} (In Progress)",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f"✅ **{task['name']}** | Start: {start_str}, End: {end_str} (Completed)")

# --------------------------------------------------
# 7) Completion: Auto-Download Schedule CSV
# --------------------------------------------------
if st.session_state.session_started and get_current_task_index(datetime.datetime.now()) >= len(st.session_state.schedule):
    df = pd.DataFrame(st.session_state.schedule)
    # Convert datetime objects to strings
    df['planned_start'] = df['planned_start'].apply(lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"))
    df['planned_end'] = df['planned_end'].apply(lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"))
    csv_data = df.to_csv(index=False)
    
    # Get overall start and end timestamps for the file name.
    start_ts = st.session_state.schedule[0]["planned_start"].strftime("%Y%m%d_%H%M%S")
    end_ts = st.session_state.schedule[-1]["planned_end"].strftime("%Y%m%d_%H%M%S")
    device = st.session_state.device.strip().replace(" ", "_") or "device"
    note = st.session_state.note.strip().replace(" ", "_") or "note"
    file_name = f"{device}_{note}_{start_ts}_{end_ts}_schedule.csv"
    
    st.download_button("Download Schedule", data=csv_data, file_name=file_name, mime="text/csv")
    
    csv_data_url = urllib.parse.quote(csv_data)
    st.components.v1.html(
        f"""
        <script>
        var a = document.createElement('a');
        a.href = 'data:text/csv;charset=utf-8,{csv_data_url}';
        a.download = '{file_name}';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        </script>
        """,
        height=0,
    )
    st.stop()

else:
    time.sleep(1)
    st.rerun()
