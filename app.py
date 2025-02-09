import requests
import json
import sqlite3
import os
import subprocess
import codecs
import sys

# ************************************************************************** //
#                             Download db Files                              //
# ************************************************************************** //


def download_file(url, filename):
  if os.path.exists(filename):
    print(f"File {filename} already exists. Skipping download.")
  else:
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    with open(filename, "wb") as f:
      f.write(response.content)
    print(f"Downloaded {filename}")


# ************************************************************************** //
#                                  Parsers                                   //
# ************************************************************************** //


def parse_emoji_test(filename):
  emoji_db = {}  # Emoji Database
  curr_group = None
  curr_subgroup = None

  with open(filename, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue

      if line.startswith("#"):
        if line.startswith("# group"):
          curr_group = line.split(":", 1)[1].strip()  # Get the group name
          if curr_group not in emoji_db:
            emoji_db[curr_group] = {}  # Create the group
        elif line.startswith("# subgroup"):
          curr_subgroup = line.split(":", 1)[1].strip()  # Get the subgroup name
          if curr_subgroup is not None:
            emoji_db[curr_group][curr_subgroup] = []  # Create the subgroup
        continue

      # Process Emoji Entry
      # Expected format example:
      # 1F600                                      ; fully-qualified     # 😀 grinning face
      try:
        left, right = line.split("#", 1)  # Code Points
        left = left.strip()  # Glyph & name
        right = right.strip()

        # Process Code Points & Status
        parts = left.split(";")
        if len(parts) < 2:
          continue  # Skip invalid lines
        codepoints_str = parts[0].strip()
        codepoints = codepoints_str.split()
        status = parts[1].strip()

        # Process Glyph & Name
        tks = right.split(" ", 1)
        emoji_glyph = tks[0].strip()
        emoji_name = tks[1].strip() if len(tks) > 1 else ""

        emoji_obj = {  # Build emoji dictionary entry
          "codepoints": codepoints,
          "status": status,
          "emoji": emoji_glyph,
          "name": emoji_name,
        }

        if curr_group and curr_subgroup:  # Add emoji to db
          emoji_db[curr_group][curr_subgroup].append(emoji_obj)

      except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Error: {e}")
        continue

  # print(
  #   # json.dumps(emoji_db, indent=2)
  # )  # This will give you a nice, formatted view of the emoji_db
  return emoji_db


def parse_unicode_data(filename):
  unicode_db = {}

  with open(filename, encoding="utf-8") as f:
    for line in f:
      # Split the line by semicolons, remove leading/trailing whitespaces
      fields = line.strip().split(";")

      # Skip malformed lines that don't have enough fields
      if len(fields) < 15:
        continue

      # Extract all fields
      code_point = fields[0]
      name = fields[1]
      general_category = fields[2]
      canonical_combining_class = fields[3]
      bidirectional_category = fields[4]
      decomposition = fields[5]
      decimal_digit_value = fields[6]
      digit_value = fields[7]
      numeric_value = fields[8]
      mirrored = fields[9]
      unicode_1_0_name = fields[10]
      iso_10646_comment = fields[11]
      uppercase_mapping = fields[12]
      lowercase_mapping = fields[13]
      titlecase_mapping = fields[14]

      # Store the data for the Unicode character in the dictionary
      unicode_db[code_point] = {
        "name": name,
        "general_category": general_category,
        "canonical_combining_class": canonical_combining_class,
        "bidirectional_category": bidirectional_category,
        "decomposition": decomposition,
        "decimal_digit_value": decimal_digit_value,
        "digit_value": digit_value,
        "numeric_value": numeric_value,
        "mirrored": mirrored,
        "unicode_1_0_name": unicode_1_0_name,
        "iso_10646_comment": iso_10646_comment,
        "uppercase_mapping": uppercase_mapping,
        "lowercase_mapping": lowercase_mapping,
        "titlecase_mapping": titlecase_mapping,
      }

  # Print the parsed data in a formatted way
  # print(json.dumps(unicode_db, indent=2))

  return unicode_db


# ************************************************************************** //
#                                     DB                                     //
# ************************************************************************** //


def setup_database(emojis, unicode_data):
  db_filename = "db/unicode.db"
  os.makedirs(os.path.dirname(db_filename), exist_ok=True)
  conn = sqlite3.connect(db_filename)
  cursor = conn.cursor()

  # Create tables
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS emojis (
            group_name TEXT,
            subgroup_name TEXT,
            codepoints TEXT,
            status TEXT,
            emoji TEXT,
            name TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS unicode_data (
            code_point TEXT PRIMARY KEY,
            name TEXT,
            general_category TEXT,
            decomposition TEXT,
            numeric_value TEXT,
            uppercase_mapping TEXT,
            lowercase_mapping TEXT,
            titlecase_mapping TEXT
        )
    """)

  # Insert emojis
  for group_name, subgroups in emojis.items():
    for subgroup_name, emoji_list in subgroups.items():
      for emoji in emoji_list:
        cursor.execute(
          """
                INSERT INTO emojis (group_name, subgroup_name, codepoints, status, emoji, name)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
          (
            group_name,
            subgroup_name,
            " ".join(emoji["codepoints"]),
            emoji["status"],
            emoji["emoji"],
            emoji["name"],
          ),
        )

  # Insert Unicode data
  for code_point, entry in unicode_data.items():
    cursor.execute(
      """
            INSERT OR REPLACE INTO unicode_data (
                code_point, name, general_category, decomposition, numeric_value,
                uppercase_mapping, lowercase_mapping, titlecase_mapping
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
      (
        code_point,
        entry["name"],
        entry["general_category"],
        entry["decomposition"],
        entry["numeric_value"],
        entry["uppercase_mapping"],
        entry["lowercase_mapping"],
        entry["titlecase_mapping"],
      ),
    )

  conn.commit()
  conn.close()
  print(f"Database created: {db_filename}")


# ************************************************************************** //
#                                   Picker                                   //
# ************************************************************************** //


def pick(emoji_lines):
  try:
    proc = subprocess.Popen(
      ["fzf", "--prompt", "Select > "],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
    )
    input_data = "\n".join(emoji_lines)
    stdout, _ = proc.communicate(input_data)
    selected_line = stdout.strip()
    if selected_line:
      return selected_line.split()[0]
  except Exception as e:
    print(f"Error invoking fzf: {e}")
  return None


# ************************************************************************** //
#                                    App                                     //
# ************************************************************************** //

if __name__ == "__main__":
  # UTF8Writer = codecs.getwriter('utf8')
  # sys.stdout = UTF8Writer(sys.stdout)
  # Handle Emoji Data
  emoji_test_url = "https://unicode.org/Public/emoji/latest/emoji-test.txt"
  emoji_test_filename = ".temp/emoji-test.txt"
  download_file(emoji_test_url, emoji_test_filename)

  # Handle Unicode Data
  unicode_data_url = "https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"
  unicode_data_filename = ".temp/UnicodeData.txt"
  download_file(unicode_data_url, unicode_data_filename)

  # Parse data
  emojis = parse_emoji_test(emoji_test_filename)
  unicode_data = parse_unicode_data(unicode_data_filename)

  # Setup SQLite database
  setup_database(emojis, unicode_data)

  # Prompt the user to pick a database
  print("\nSelect DB:")
  print("1 - Emoji Database (emoji_db.json)")
  print("2 - Unicode Database (unicode_db.json)")
  choice = input("Enter 1 or 2: ").strip()

  conn = sqlite3.connect("db/unicode.db")
  cursor = conn.cursor()

  if choice == "1":
    cursor.execute("""
          SELECT group_name, subgroup_name, emoji, name FROM emojis
      """)
    rows = cursor.fetchall()
    lines = [f"{row[2]} {row[3]} [{row[0]} / {row[1]}]" for row in rows]
  elif choice == "2":
    cursor.execute("""
          SELECT code_point, name FROM unicode_data
      """)
    rows = cursor.fetchall()
    # Convert code points to the actual Unicode glyph
    # lines = [f"{chr(int(row[0], 16))} {row[1]} (U+{row[0]})" for row in rows]
    lines = [f"{row[0]} {row[1]}" for row in rows]
  else:
    print("Invalid choice. Exiting.")
    exit()

  picked = pick(lines)
  conn.close()

  if picked:
    print(chr(int(picked, 16)))
  else:
    print("No selection made.")
