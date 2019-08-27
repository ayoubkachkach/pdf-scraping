"""Extract text from PDF files and organize in XML."""
import argparse
import glob
import os
import re
import textract

from lxml import etree as ET

PARSER = argparse.ArgumentParser(description='Make story dataset.')
PARSER.add_argument('--path_regex', required=True)

def split_text_regex(text, path):
    max_count = 0
    count = 0
    for i in range(len(text[:150]) - 1):
        if text[i] == '\n' and text[i + 1] != '\n':
            max_count = max(max_count, count + 1)
            count = 0
            continue

        if text[i] == text[i + 1] == '\n':
            count += 1

    max_count = max(max_count, count)
    max_count = max(max_count, 1)  # max_count shouldn't be 0.
    # Search for: Sequence of anything that's not line breaks (the title,
    # hopefully!) followed by a sequence of line breaks (separation between
    # title and body) followed by whatever (body).
    match = re.search(r'([\s\S]+?)[\r\n]{%s}([\s\S]+)' % max_count, text)
    if not match:
        print('Story in %s gave no match!' % path)
        return None, None

    # Extract title and body from regexp results.
    title = match.group(1)
    body = match.group(2)

    return title, body


def strip_chars(text, extra=u''):
    """Strip text from control characters not supported by XML."""
    remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F%s]'
                           % extra)
    return remove_re.sub('', text)


def pdf_to_xml(path, story_id):
    """Converts pdf of story to xml.

    Args:
        path: path to pdf.
        story_id: id to be assigned to the story.

    Returns:
        ET.Element object representing the XML node of the story.
    """
    raw_text = textract.process(path)
    # Convert bytes-like raw_text to utf-8 encoded string.
    text = raw_text.decode(u'utf-8')

    title, body = split_text_regex(text, path)
    if not title and not body:
        return None

    story_node = ET.Element('story')
    id_node = ET.SubElement(story_node, 'id')
    id_node.text = str(story_id)

    filename_node = ET.SubElement(story_node, 'id')
    filename_node.text = str(path.split('/')[-1])

    title_node = ET.SubElement(story_node, 'title')
    title_node.text = strip_chars(title)

    body_node = ET.SubElement(story_node, 'body')
    body_node.text = strip_chars(body)

    return story_node


if __name__ == '__main__':
    args = PARSER.parse_args()
    path_regex = args.path_regex
    path_regex = os.path.expanduser(path_regex)
    print('Got %s' % path_regex)

    filenames = glob.glob(path_regex)
    print('Found %s filenames' % filenames)
    stories_tag = ET.Element('stories')
    for story_id, filename in enumerate(filenames):
        story_tag = pdf_to_xml(filename, story_id)
        if not story_tag:
            continue
        stories_tag.append(story_tag)

    tree = ET.ElementTree(stories_tag)
    with open('ouput.txt', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)
