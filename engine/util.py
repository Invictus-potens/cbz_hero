import re
import feedback

def regexGroup(pattern, target, group=1):
    """ Given a pattern and a string, return capturing group 1 by default
    """
    m = re.match(pattern, target)

    if m:
        return m.group(group)

def padChapterNumber(number, width=4):
    """ Zero-pad a chapter number, keeping any half-chapter suffix (21.5 -> 0021.5)

    Keeps chapter files listing in reading order.
    """
    parts = str(number).split('.')
    parts[0] = parts[0].zfill(width)

    return '.'.join(parts)

def unpackJs(source):
    """ Decode javascript packed with Dean Edwards' p,a,c,k,e,d packer

    Several sites deliver their image URLs this way. Returns the unpacked
    source, or None if the data was not packed.
    """
    packed = re.search("\\}\\('(.*?)',([0-9]+),([0-9]+),'(.*?)'\\.split\\('\\|'\\)", source, re.S)

    if not packed:
        return None

    payload, base, count = packed.group(1), int(packed.group(2)), int(packed.group(3))
    keywords = packed.group(4).split('|')

    digits = "0123456789abcdefghijklmnopqrstuvwxyz"

    def toBase36(number):
        encoded = ""
        while number > 0:
            encoded = digits[number % 36] + encoded
            number = number // 36
        return encoded or "0"

    def symbolFor(number):
        prefix = "" if number < base else symbolFor(number // base)
        remainder = number % base
        # the packer switches to raw character codes past base 36
        return prefix + (chr(remainder + 29) if remainder > 35 else toBase36(remainder) )

    substitutions = {}
    for i in range(count):
        symbol = symbolFor(i)
        substitutions[symbol] = keywords[i] if i < len(keywords) and keywords[i] else symbol

    unpacked = re.sub("\\b\\w+\\b", lambda m: substitutions.get(m.group(0), m.group(0) ), payload)

    return unpacked.replace("\\'", "'").replace('\\"', '"')

def naturalSort(array, keypattern='.*?([0-9]+)', group=1):
    """ Use a natural sorting on first number in the string,
    
    Or, specify a pattern, and matching using the contents of the capturing group as the key
    """
    def naturalSortKey(string):
        m = re.match(keypattern, string)
        if m:
            gv = m.group(group)
            if re.match("^[0-9]+(\\.[0-9]+)?$", gv ):
                # number, expect possibility of floats from custom strings
                return float(gv)
            # Simply the plain targeted group
            return gv

        # Return the original string, for something to compare on
        return string


    array.sort(key=naturalSortKey)
