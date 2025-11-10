import pandas as pd
import matplotlib.pyplot as plt

# 1) Load CSVs
points = pd.read_csv("data/processed/iclr_points.csv", encoding="utf-8-sig")
areas  = pd.read_csv("data/processed/area.csv", encoding="utf-8-sig")

# 2) Normalize column names to lowercase (avoids 'Area' vs 'area' bugs)
points.columns = points.columns.str.strip().str.lower()
areas.columns  = areas.columns.str.strip().str.lower()

# 3) Quick sanity check: required columns
for need, dfname, cols in [
    ("iclr_points.csv", "points", ["area", "iclr_points"]),
    ("area.csv", "areas", ["area", "parent_area"])
]:
    for c in cols:
        if c not in eval(dfname).columns:
            raise KeyError(f"Column '{c}' not found in {need}. Available: {list(eval(dfname).columns)}")

# 4) Build Area -> Parent mapping (area.csv has multiple rows per area; we only need one)
area_to_parent = (
    areas[["area", "parent_area"]]
    .drop_duplicates(subset=["area"])
)

# 5) Merge parent into points
df = points.merge(area_to_parent, on="area", how="left")
df["parent_area"] = df["parent_area"].fillna("other")

# 6) Sort so same parent colors stay together; inside each group sort by iclr_points
df = df.sort_values(["parent_area", "iclr_points"], ascending=[True, True])

# 7) Give each parent one color (no legend shown)
palette = list(plt.cm.tab10.colors)
parents = df["parent_area"].unique().tolist()
color_map = {p: palette[i % len(palette)] for i, p in enumerate(parents)}
bar_colors = df["parent_area"].map(color_map)

# 8) Plot
plt.figure(figsize=(11, 8))
plt.barh(df["area"], df["iclr_points"], color=bar_colors)

plt.title("ICLR Points: How Many ICLR Publications Is One Paper in Each Area?", fontsize=14)
plt.xlabel("ICLR Points")
plt.ylabel("Area")

# value labels on bars
for i, v in enumerate(df["iclr_points"]):
    plt.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9)

plt.grid(axis="x", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()

