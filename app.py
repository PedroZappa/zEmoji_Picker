import requests
import json
import os

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
          continue # Skip invalid lines
        codepoints_str = parts[0].strip()
        codepoints = codepoints_str.split()
        status = parts[1].strip()

        # Process Glyph & Name
        tks = right.split(" ", 1)
        emoji_glyph = tks[0].strip()
        emoji_name = tks[1].strip() if len(tks) > 1 else ""

        emoji_obj ={ # Build emoji dictionary entry
          "codepoints": codepoints,
          "status": status,
          "emoji": emoji_glyph,
          "name": emoji_name,
        }

        if curr_group and curr_subgroup: # Add emoji to db
          emoji_db[curr_group][curr_subgroup].append(emoji_obj)

      except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Error: {e}")
        continue

  return emoji_db

# ************************************************************************** //
#                                     DB                                     //
# ************************************************************************** //

def save_db_as_json(db, out_filename):
  # ensure out dir exists
  os.makedirs(os.path.dirname(out_filename), exist_ok=True)
  with open(out_filename, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2, ensure_ascii=False)
  
  print(f"Saved db to {out_filename}")

# ************************************************************************** //
#                                    App                                     //
# ************************************************************************** //

if __name__ == "__main__":
  # URLs for the Unicode data files
  emoji_test_url = "https://unicode.org/Public/right/latest/right-test.txt"
  unicode_data_url = "https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"

  # File names for the downloaded files
  emoji_test_filename = "db/emoji-test.txt"
  unicode_data_filename = "db/UnicodeData.txt"

  # Download right/Unico db files
  download_file(emoji_test_url, emoji_test_filename)
  download_file(unicode_data_url, unicode_data_filename)

  # Parse and save db files
  emoji_db = parse_emoji_test(emoji_test_filename)
  save_db_as_json(emoji_db, "db/emoji_db.json")
