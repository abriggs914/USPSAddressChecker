from typing import Literal, Optional, Iterable, Any

import math
import pandas as pd
from streamlit_js_eval import streamlit_js_eval

import streamlit as st
import datetime

from utils.colour_utility import Colour

#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

VERSION = \
	"""	
		Streamlit utility functions
		Version..............1.11
		Date...........2026-04-08
		Author(s)....Avery Briggs
		"""


def VERSION_DETAILS():
	return VERSION.lower().split("version")[0].strip()


def VERSION_NUMBER():
	return float(".".join(VERSION.lower().split("version")[-1].split("today")[0].split(".")[-2:]).strip())


def VERSION_DATE():
	return datetime.datetime.strptime(VERSION.lower().split("today")[-1].split("author")[0].split(".")[-1].strip(),
									  "%Y-%m-%d")


def VERSION_AUTHORS():
	return [w.removeprefix(".").strip().title() for w in VERSION.lower().split("author(s)")[-1].split("..") if
			w.strip()]


#######################################################################################################################
#######################################################################################################################
#######################################################################################################################


def aligned_text(
		txt: str,
		tag_style: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p", "span"] = "h1",
		h_align: Literal["left", "center", "right"] = "center",
		colour: str = "#FFFFFF",
		line_height: int = 1
) -> str:
	"""
		Return formatted HTML, and in-line CSS to h_align a given text in a container.
		Use with streamlit's markdown function and with 'unsafe_allow_html' set to True.
		See coloured_text() for streamlined-colour-only functionality.
		"""
	return f"<{tag_style} style='line-height: {line_height}; text-align: {h_align}; color: {colour};'>{txt}</{tag_style}>"


def hide_image_fullscreen_buttons():
	"""
		Remove ALL fullscreen buttons for images created using streamlit's image function.
		https://discuss.streamlit.io/t/hide-fullscreen-option-when-displaying-images-using-st-image/19792
		"""
	hide_img_fs = '''
		<style>
		button[title="View fullscreen"]{
				visibility: hidden;}
		</style>
		'''
	st.markdown(hide_img_fs, unsafe_allow_html=True)

	hide_img_fs


def center_fullscreen_images():
	"""
		Center an image when in fullscreen browsing mode
		https://discuss.streamlit.io/t/how-can-i-center-a-picture/30995/3
		"""
	st.markdown(
		"""
				<style>
						button[title^=Exit]+div [path_data-testid=stImage]{
								text-align: center;
								display: block;
								margin-left: auto;
								margin-right: auto;
								width: 100%;
						}
				</style>
				""", unsafe_allow_html=True
	)


def coloured_text(
		text: str,
		colour: str | Colour = "#000000",
		html_tags: str = "span",
		call: bool = False,
		style_only: bool = False
) -> str:
	"""
		Return an HTML string of text styled with a colour.
		See aligned_text() for more functionality

		:param text: Text to be rendered.
		:param colour: Text foreground colour.
		:param html_tags: The HTML text tag you want to display the text with. Wide-open and not fully tested. stick to common text elements (headers, paragraphs, etc...)
		:param call: If True the result will immediately be displayed by calling st.markdown. Not recommended if you want to place your text within another element or container.
		:param style_only: If True return the formatted HTML style string.
		:return: Formatted HTML string.
		"""
	style = f"style='color:{Colour(colour).hex_code};'"
	html = f"<{html_tags}{' ' + style}'>{text}</{html_tags}>"
	if call:
		st.markdown(html, unsafe_allow_html=True)
	if style_only:
		return style
	return html


def rerun():
	# https://discuss.streamlit.io/t/is-it-possible-to-create-a-button-to-reset-relaod-the-whole-dashboard/6615/3
	import pyautogui
	pyautogui.hotkey("ctrl", "F5")


def screen_dimensions() -> tuple[Optional[int], Optional[int]]:
	"""
		Use JavaScript to retrieve the screen's Width and Height as integers.
		:return: (Width, Height) as an integer tuple. May return None.
		"""
	return (
		streamlit_js_eval(js_expressions='parent.innerWidth', key='SCR_W'),
		streamlit_js_eval(js_expressions='parent.innerHeight', key='SCR_H')
	)


def display_df(
	df: pd.DataFrame | pd.Series,
	title: Optional[str] = None,
	hide_index: str | bool = "if_int",
	show_shape: bool = True,
	fail_safe: Optional[Any] = None,

	# params for st.dataframe 20250325
	width: int | None = None,
	height: int | None = None,
	use_container_width: bool = False,
	column_order: Iterable[str] | None = None,
	column_config: Any | None = None,
	key: Any | None = None,
	on_select: Literal["ignore", "rerun"] | Any = "ignore",
	selection_mode: Any = "multi-row"
):
	try:
		title = title if title else ""
		shape = df.shape
		if show_shape:
			title = f"{title} ({shape[0]} Rows".strip()
			title += f" x {shape[1]} Cols)" if len(shape) > 1 else ")"

		if title:
			st.write(title)

		if hide_index == "if_int":
			hide_index = str(df.index.dtype).lower() == "int64"

		if height is None:
			height = "auto"

		# st.write(f"{title=}, {hide_index=}")
		stdf = st.dataframe(
			data=df,
			hide_index=hide_index,
			width=width,
			height=height,
			use_container_width=use_container_width,
			column_order=column_order,
			column_config=column_config,
			key=key,
			on_select=on_select,
			selection_mode=selection_mode
		)
	except Exception as e:
     	if isinstance(fail_safe, bool):
			fail_safe = st.write if fail_safe else None
		if fail_safe is not None:			
			stdf = None
			if callable(fail_safe):
				try:
					fail_safe(df)
				except:
					pass
			else:
				st.write(fail_safe)
		else:
			raise e
	return stdf


@st.cache_data(ttl=None, show_spinner=True)
def load_pdf_binary(pdf_file):
	with open(pdf_file, "rb") as f:
		return f.read()
	

@st.cache_data(show_spinner=False)
def split_frame(input_df: pd.DataFrame, rows: int):
	if input_df.shape[0] <= rows:
		return [input_df]
	# st.write(f"{rows=}")
	# st.write(input_df.head(3))
	df = [input_df.reset_index().loc[i : i + rows - 1, :] for i in range(0, input_df.shape[0] + rows, rows)]
	return df


def display_df_paginated(
		df: pd.DataFrame | pd.Series,
		title: Optional[str] = None,
		hide_index: str | bool = "if_int",
		show_shape: bool = True,
		batch_size_options: list[int] = (25, 50, 100),

		# params for st.dataframe 20250325
		width: int | None = None,
		height: int | None = None,
		use_container_width: bool = False,
		column_order: Iterable[str] | None = None,
		column_config: Any | None = None,
		key: Any | None = None,
		on_select: Literal["ignore", "rerun"] | Any = "ignore",
		selection_mode: Any = "multi-row"		
):
	
	if key is None:
		# sub_widget_keys = f"stdf_paginated_{datetime.datetime.now():%Y%m%d%%H%M%S}"
		msg = f"You must pass a key for a paginated dataframe widget. Otherwise sub-widgets won't have state-persistence."
		st.error(msg)
		raise ValueError(msg)
	else:
		sub_widget_keys = key

	top_menu = st.columns(3)
	with top_menu[0]:
		sort = st.radio(
			label="Sort Data",
			options=["Yes", "No"],
			horizontal=1,
			index=1,
			key=f"{sub_widget_keys}_radio_sort_col"
		)
	if sort == "Yes":
		with top_menu[1]:
			sort_field = st.selectbox("Sort By", options=df.columns)
		with top_menu[2]:
			sort_direction = st.radio(
				label="Direction",
				options=["⬆️", "⬇️"],
				horizontal=True,
				key=f"{sub_widget_keys}_radio_sort_dir"
			)
		df.sort_values(
			by=sort_field,
			ascending=sort_direction == "⬆️",
			ignore_index=True,
			inplace=True
		)
	pagination = st.container()

	bottom_menu = st.columns((4, 1, 1))
	with bottom_menu[2]:
		batch_size = st.selectbox(
			label="Page Size",
			options=batch_size_options,
			key=f"{sub_widget_keys}_selectbox_batch_size"
		)
	with bottom_menu[1]:
		total_pages = (
			math.ceil(len(df) / batch_size) if int(len(df) / batch_size) > 0 else 1
		)
		current_page = st.number_input(
			label="Page",
			min_value=1,
			max_value=total_pages,
			step=1,
			key=f"{sub_widget_keys}_number_input_pages"
		)
	with bottom_menu[0]:
		st.markdown(f"Page **{current_page}** of **{total_pages}** ")
		st.markdown(f"**{df.shape[0]}** total records")

	pages = split_frame(df, batch_size)
	# st.write(f"{len(pages)=}")
	# st.write(f"{[len(p) for p in pages]=}")
	# st.write(f"{batch_size=}")
	with pagination:
		return display_df(
			df=pages[current_page - 1] if pages else pd.DataFrame(data=[{"data": None}]),
			title=title,
			hide_index=hide_index,
			show_shape=show_shape,

			width=width,
			height=height,
			use_container_width=use_container_width,
			column_order=column_order,
			column_config=column_config,
			key=key,
			on_select=on_select,
			selection_mode=selection_mode
		)  
  

def in_streamlit() -> bool:
		"""Detect whether there is an active Streamlit script context"""
		try:
				from streamlit.runtime.scriptrunner import get_script_run_ctx
				return get_script_run_ctx() is not None
		except Exception:
				return False


if __name__ == '__main__':
	st.set_page_config(layout="wide")

	text = "Hello World"
	st.markdown(aligned_text(text, colour="#569072", tag_style="h6", line_height=50), unsafe_allow_html=True)
