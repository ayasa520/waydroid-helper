import base64
import struct


class AbxDecodeError(Exception):
    pass

class XmlType:
    START_DOCUMENT = 0
    END_DOCUMENT = 1
    START_TAG = 2
    END_TAG = 3
    TEXT = 4
    ATTRIBUTE = 15

class DataType:
    TYPE_NULL = 1 << 4
    TYPE_STRING = 2 << 4
    TYPE_STRING_INTERNED = 3 << 4
    TYPE_BYTES_HEX = 4 << 4
    TYPE_BYTES_BASE64 = 5 << 4
    TYPE_INT = 6 << 4
    TYPE_INT_HEX = 7 << 4
    TYPE_LONG = 8 << 4
    TYPE_LONG_HEX = 9 << 4
    TYPE_FLOAT = 10 << 4
    TYPE_DOUBLE = 11 << 4
    TYPE_BOOLEAN_TRUE = 12 << 4
    TYPE_BOOLEAN_FALSE = 13 << 4

class XMLElement:
    def __init__(self, tag):
        self.tag = tag
        self.text = ""
        self.attrib = {}
        self.children = []

    def add_child(self, child):
        self.children.append(child)

class AbxReader:
    def __init__(self, filename):
        self.stream = open(filename, "rb")
        self.interned_strings = []
        self.MAGIC = b'ABX\0'

    def read(self, is_multi_root=False):
        if self.stream.read(4) != self.MAGIC:
            raise AbxDecodeError("Invalid magic number")
        self.skip_header_extension()

        element_stack = []
        root = None
        if is_multi_root:
            root = XMLElement("root")
            element_stack.append(root)

        while True:
            token_bytes = self.stream.read(1)
            if not token_bytes:
                break
            token = token_bytes[0]
            xml_type = token & 0x0F
            data_type = token & 0xF0

            if xml_type == XmlType.START_DOCUMENT:
                continue
            elif xml_type == XmlType.END_DOCUMENT:
                if not element_stack or (is_multi_root and len(element_stack) == 1):
                    break
                raise AbxDecodeError("Unclosed elements at END_DOCUMENT")
            elif xml_type == XmlType.START_TAG:
                if data_type != DataType.TYPE_STRING_INTERNED:
                    raise AbxDecodeError("Invalid START_TAG type")
                tag = self.read_interned_string()
                element = XMLElement(tag)
                if not element_stack:
                    root = element
                else:
                    element_stack[-1].add_child(element)
                element_stack.append(element)
            elif xml_type == XmlType.END_TAG:
                tag = self.read_interned_string()
                if not element_stack or (is_multi_root and len(element_stack) == 1):
                    raise AbxDecodeError("Unexpected END_TAG")
                if element_stack[-1].tag != tag:
                    raise AbxDecodeError("Mismatched END_TAG")
                element_stack.pop()
            elif xml_type == XmlType.TEXT:
                value = self.read_string_raw()
                if not value.strip():
                    continue
                if not element_stack:
                    raise AbxDecodeError("Unexpected TEXT")
                element_stack[-1].text += value
            elif xml_type == XmlType.ATTRIBUTE:
                name = self.read_interned_string()
                value = self.read_value_by_type(data_type)
                element_stack[-1].attrib[name] = value
            else:
                # Skip unknown
                self.read_value_by_type(data_type)

        if not root:
            raise AbxDecodeError("No root element found")

        return root

    def read_value_by_type(self, dtype):
        if dtype == DataType.TYPE_NULL:
            return "null"
        elif dtype == DataType.TYPE_BOOLEAN_TRUE:
            return "true"
        elif dtype == DataType.TYPE_BOOLEAN_FALSE:
            return "false"
        elif dtype == DataType.TYPE_INT:
            return str(self.read_int())
        elif dtype == DataType.TYPE_INT_HEX:
            return hex(self.read_int())
        elif dtype == DataType.TYPE_LONG:
            return str(self.read_long())
        elif dtype == DataType.TYPE_LONG_HEX:
            return hex(self.read_long())
        elif dtype == DataType.TYPE_FLOAT:
            return str(self.read_float())
        elif dtype == DataType.TYPE_DOUBLE:
            return str(self.read_double())
        elif dtype == DataType.TYPE_STRING:
            return self.read_string_raw()
        elif dtype == DataType.TYPE_STRING_INTERNED:
            return self.read_interned_string()
        elif dtype == DataType.TYPE_BYTES_HEX:
            length = self.read_short()
            data = self.stream.read(length)
            return data.hex()
        elif dtype == DataType.TYPE_BYTES_BASE64:
            length = self.read_short()
            data = self.stream.read(length)
            return base64.b64encode(data).decode()
        else:
            raise AbxDecodeError(f"Unknown data type: {hex(dtype)}")

    def skip_header_extension(self):
        while True:
            token = self.stream.read(1)[0]
            xml_type = token & 0x0F
            data_type = token & 0xF0
            if xml_type == XmlType.START_DOCUMENT:
                self.stream.seek(-1, 1)
                break
            self.read_value_by_type(data_type)

    def read_byte(self):
        return self.stream.read(1)[0]

    def read_short(self):
        return struct.unpack(">H", self.stream.read(2))[0]

    def read_int(self):
        return struct.unpack(">I", self.stream.read(4))[0]

    def read_long(self):
        return struct.unpack(">Q", self.stream.read(8))[0]

    def read_float(self):
        return struct.unpack(">f", self.stream.read(4))[0]

    def read_double(self):
        return struct.unpack(">d", self.stream.read(8))[0]

    def read_string_raw(self):
        length = self.read_short()
        return self.stream.read(length).decode("utf-8")

    def read_interned_string(self):
        reference = struct.unpack(">h", self.stream.read(2))[0]
        if reference == -1:
            value = self.read_string_raw()
            self.interned_strings.append(value)
            return value
        return self.interned_strings[reference]

    def to_xml_string(self, element=None, indent=0):
        if element is None:
            element = self.read()

        lines = []
        if indent == 0:
            lines.append("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>")

        ind = " " * indent
        attrs = " ".join(f'{k}="{v}"' for k, v in element.attrib.items())
        tag_open = f"{ind}<{element.tag}"
        if attrs:
            tag_open += f" {attrs}"

        if not element.children and not element.text:
            tag_open += "/>"
            lines.append(tag_open)
        else:
            tag_open += ">"
            if element.text:
                tag_open += element.text
                if not element.children:
                    tag_open += f"</{element.tag}>"
                    lines.append(tag_open)
                else:
                    lines.append(tag_open)
            else:
                lines.append(tag_open)

            for child in element.children:
                lines.append(self.to_xml_string(child, indent + 2))

            if element.children:
                lines.append(f"{ind}</{element.tag}>")
        return "\n".join(lines) if indent == 0 else "\n".join(lines)
