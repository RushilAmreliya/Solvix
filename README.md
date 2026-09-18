# Convective Scale Nowcasting System (SIH26084)

A real-time, multi-source data fusion based Nowcasting System for thunderstorms, hail, and cloudbursts. Developed for Smart India Hackathon.

## Project Structure
```text
.
├── docs/                   # Project documentation and planning
│   ├── problem_statement.md
│   ├── idea_summary.md
│   ├── architecture.md
│   ├── tech_stack.md
│   ├── data_sources.md
│   ├── scope.md
│   ├── development_roadmap.md
│   └── team_roles.md
├── src/                    # Source code (to be implemented)
│   ├── backend/            # FastAPI server and Data Simulator
│   ├── engine/             # PySTEPS nowcasting and hazard logic
│   └── frontend/           # Streamlit GIS Dashboard
├── data/                   # Sample historical datasets for simulation
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## How to Run (Prototype Concept)

*Note: This is a placeholder for the final prototype structure.*

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the Data Simulator and Backend:**
   ```bash
   # Terminal 1
   uvicorn src.backend.main:app --reload
   ```
3. **Start the Frontend Dashboard:**
   ```bash
   # Terminal 2
   streamlit run src/frontend/app.py
   ```

## Documentation
Please refer to the `/docs` folder for comprehensive planning, architecture, and scope details, including our primary focus on the North-East India / Assam region and rapid Streamlit deployment.
