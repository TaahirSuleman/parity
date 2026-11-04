"""The SAM replay's pure parts, offline."""
from eval.sam_boxes import box_prompt, box_token, chunks, parse_boxes
from parity.store.models import BBox


def test_box_token_is_inclusive_source_pixels_inside_the_frame():
    assert box_token(1, BBox(x_min=169, y_min=131, x_max=232, y_max=154), 1280, 720) == "1<|box;x1=216;y1=94;x2=296;y2=110;w=1280;h=720|>"
    assert box_token(2, BBox(x_min=0, y_min=0, x_max=1000, y_max=1000), 640, 480) == "2<|box;x1=0;y1=0;x2=639;y2=479;w=640;h=480|>"


def test_box_prompt_has_one_frame_header_and_comma_separated_objects():
    p = box_prompt({1: BBox(x_min=0, y_min=0, x_max=500, y_max=500), 2: BBox(x_min=500, y_min=500, x_max=1000, y_max=1000)}, 100, 100)
    assert p.startswith("<0f>1<|box;") and ",2<|box;" in p and p.count("<0f>") == 1


def test_parse_boxes_reads_objects_and_skips_masks():
    text = "<0f>1<|box;x1=222;y1=95;x2=290;y2=108;w=1280;h=720|><|mask;x=0;y=0;data=14,69,~!!abc|>,3<|box;x1=0;y1=0;x2=639;y2=479;w=640;h=480|><|mask;x=0;y=0;data=1,1,~!|>\n"
    boxes = parse_boxes(text)
    assert sorted(boxes) == [1, 3]
    assert boxes[1] == BBox(x_min=173, y_min=132, x_max=227, y_max=151)
    assert boxes[3] == BBox(x_min=0, y_min=0, x_max=1000, y_max=1000)


def test_parse_boxes_of_nothing_is_empty():
    assert parse_boxes("") == {}


def test_chunks_respects_the_limit():
    assert chunks([1, 2, 3], 2) == [[1, 2], [3]]
