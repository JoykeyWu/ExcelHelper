"""Step execution engine — pure pandas, no LLM dependency."""
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"


class ExecutionError(Exception):
    pass


def execute_steps(steps: list[dict], input_file_path: str) -> tuple[pd.DataFrame, str]:
    """Run a list of steps, return (final_dataframe, output_file_path)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df: pd.DataFrame | None = None
    output_path = ""

    for i, step in enumerate(steps):
        action = step["action"]
        params = step.get("params", {})

        try:
            df, output_path = _dispatch(action, params, df, input_file_path)
        except Exception as e:
            raise ExecutionError(
                f"步骤 {i+1} ({action}) 执行失败: {e}"
            ) from e

    return df, output_path


def _resolve_path(file_path: str, input_file_path: str) -> str:
    """Resolve file paths: {{input}} → actual uploaded file, relative → data/."""
    if file_path == "{{input}}":
        return input_file_path
    p = Path(file_path)
    if p.is_absolute() and p.exists():
        return str(p)
    candidate = DATA_DIR / file_path
    if candidate.exists():
        return str(candidate)
    return file_path


# ── action handlers ──────────────────────────────────────

def _dispatch(action: str, params: dict, df: pd.DataFrame | None, input_path: str):
    if action == "load_data":
        return _load_data(params, input_path), ""

    if df is None:
        raise ExecutionError("没有可操作的数据，请先用 load_data 读取文件")

    if action == "merge":
        return _merge(df, params, input_path), ""
    elif action == "groupby_agg":
        return _groupby_agg(df, params), ""
    elif action == "filter":
        return _filter(df, params), ""
    elif action == "sort":
        return _sort(df, params), ""
    elif action == "add_total_row":
        return _add_total_row(df, params), ""
    elif action == "add_column":
        return _add_column(df, params), ""
    elif action == "pivot_table":
        return _pivot_table(df, params), ""
    elif action == "export":
        output_path = _export(df, params)
        return df, output_path
    else:
        raise ExecutionError(f"未知步骤类型: {action}")


def _load_data(params: dict, input_path: str) -> pd.DataFrame:
    file_path = _resolve_path(params["file_path"], input_path)
    sheet = params.get("sheet_name")

    # auto-detect file type from extension, more reliable than params
    if file_path.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path, sheet_name=sheet or 0)
    else:
        return pd.read_csv(file_path, encoding="utf-8-sig")


def _merge(df: pd.DataFrame, params: dict, input_path: str) -> pd.DataFrame:
    right_path = _resolve_path(params["right_file"], input_path)
    right_type = "excel" if right_path.endswith(".xlsx") else "csv"
    right_df = (
        pd.read_excel(right_path) if right_type == "excel"
        else pd.read_csv(right_path, encoding="utf-8-sig")
    )

    on = params.get("on")
    how = params.get("how", "left")

    if isinstance(on, dict):
        left_on = on["left"]
        right_on = on["right"]
        return df.merge(right_df, left_on=left_on, right_on=right_on, how=how)
    else:
        return df.merge(right_df, on=on, how=how)


def _groupby_agg(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    group_by = params["group_by"]
    aggregations = params["aggregations"]
    rename = params.get("rename", {})

    if isinstance(group_by, str):
        group_by = [group_by]

    result = df.groupby(group_by, as_index=False).agg(aggregations)

    # flatten MultiIndex columns
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = ["_".join(col).strip("_") for col in result.columns.values]

    if rename:
        result.rename(columns=rename, inplace=True)

    return result


def _filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    col = params["column"]
    op = params["operator"]
    val = params["value"]

    if op == "==":
        return df[df[col] == val]
    elif op == "!=":
        return df[df[col] != val]
    elif op == ">":
        return df[df[col] > val]
    elif op == "<":
        return df[df[col] < val]
    elif op == ">=":
        return df[df[col] >= val]
    elif op == "<=":
        return df[df[col] <= val]
    elif op == "in":
        return df[df[col].isin(val if isinstance(val, list) else [val])]
    elif op == "contains":
        return df[df[col].astype(str).str.contains(str(val))]
    else:
        raise ExecutionError(f"未知筛选操作符: {op}")


def _sort(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    return df.sort_values(by=params["by"], ascending=params.get("ascending", True))


def _add_total_row(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    columns = params.get("columns", [])
    methods = params.get("methods", {})
    first_col = params.get("label_column") or df.columns[0]

    total = {first_col: "合计"}
    for col in df.columns:
        if col == first_col:
            continue
        if col in columns or col in methods:
            method = methods.get(col, "sum")
            if method == "sum":
                total[col] = df[col].sum()
            elif method == "mean":
                total[col] = df[col].mean()
            else:
                total[col] = ""
        else:
            total[col] = ""

    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)


def _add_column(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    name = params["name"]
    expression = params["expression"]
    df = df.copy()
    df[name] = df.eval(expression)
    return df


def _pivot_table(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    index = params["index"]
    columns = params.get("columns")
    values = params["values"]
    aggfunc = params.get("aggfunc", "sum")

    result = df.pivot_table(
        index=index,
        columns=columns,
        values=values,
        aggfunc=aggfunc,
        fill_value=0,
    )
    return result.reset_index()


def _export(df: pd.DataFrame, params: dict) -> str:
    file_name = params.get("file_name", "output.xlsx")
    output_path = OUTPUT_DIR / file_name
    df.to_excel(str(output_path), index=False)
    return str(output_path)
