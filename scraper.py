"""Extract text from PDF files and organize in XML."""
import argparse
import glob
import os
import re
import textract
from tika import parser
from lxml import etree as ET

PARSER = argparse.ArgumentParser(description='Make story dataset.')
PARSER.add_argument('--path', required=True)
PARSER.add_argument('--extractor', default='basic')
PARSER.add_argument('--tika_server', default='http://localhost:9998/')

def split_text_regex(text, path):
    """Splits text into title and body at the earliest maximum number of
    consecutive line breaks

    Args:
        text: text to be split into title and body.
        path: path linking to source of text.

    Returns:
        Tuple of title, body.
    """
    max_count = 0
    count = 0
    for i in range(len(text[:150]) - 1):
        if text[i] == '\n' and text[i + 1] != '\n':
            max_count = max(max_count, count + 1)
            count = 0
        elif text[i] == text[i + 1] == '\n':
            count += 1

    max_count = max(max_count, count) # update max_count one last time.
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


def to_xml(body, title, path, story_id):
    """Create xml of story from its components.

    Args:
        title: title of story.
        body: body of story.
        story_id: id to be assigned to the story.

    Returns:
        ET.Element object representing the XML node of the story.
    """
    # Convert bytes-like raw_text to utf-8 encoded string.
    if not title and not body:
        return None

    story_node = ET.Element('story')
    id_node = ET.SubElement(story_node, 'id')
    id_node.text = str(story_id)

    filename_node = ET.SubElement(story_node, 'filename')
    filename_node.text = str(path.split('/')[-1])

    title_node = ET.SubElement(story_node, 'title')
    title_node.text = strip_chars(title)

    body_node = ET.SubElement(story_node, 'body')
    body_node.text = strip_chars(body)

    return story_node

not_parsed = []

def tika_extract(path, server='http://localhost:9998/'):
    os.environ['TIKA_CLIENT_ONLY'] = 'True'
    os.environ['TIKA_SERVER_ENDPOINT'] = server
    print('Calling tika server using %s' % server)
    try:
        print('processing %s' % path)
        raw_text = parser.from_file(path)['content']
    except KeyError:
        print("Tika couldn't parse content for %s, skipping ..." % path)

    if not raw_text:
        print('Filename %s could not be parsed' % path)
        not_parsed.append(path)
        return None, None

    lines = raw_text.splitlines()
    title_line_num = -1
    for line_num, line in enumerate(lines):
        if line.strip():
            title = strip_chars(line)
            title_line_num = line_num
            break

    if title_line_num == -1:
        print('No title found for file in %s' % path)

    # Only keep lines that contain non-whitespace characters.
    lines = [strip_chars(line) for line in lines if line.strip()]
    body = ''.join(lines)

    return title, body


if __name__ == '__main__':
    args = PARSER.parse_args()
    path = os.path.expanduser(args.path)
    print('Got %s' % path)

    filenames = glob.glob(path + "*pdf")
    print('Found %s filenames' % filenames)
    stories_tag = ET.Element('stories')
    for story_id, filename in enumerate(filenames):
        if args.extractor == 'tika':
            title, body = tika_extract(filename, server=args.tika_server)
        elif args.extractor == 'textractor':
            raw_text = textract.process(filename)
            text = raw_text.decode(u'utf-8')
            title, body = split_text_regex(text, filename)
        else:
            raw_text = textract.process(filename)
            body = raw_text.decode(u'utf-8')
            title = filename.split('/')[-1][:-4] # Strip absolute path and .pdf extension

        story_tag = to_xml(body, title, filename, story_id)
        if not story_tag:
            continue

        stories_tag.append(story_tag)

    tree = ET.ElementTree(stories_tag)
    with open('ouput.txt', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)

    not_parsed = [filename.split('/')[-1] for filename in not_parsed]
    print('-------\nCould not be parsed:')
    for filename in not_parsed:
        print(filename)

class A:
    def speak():
        print("Hey!")

