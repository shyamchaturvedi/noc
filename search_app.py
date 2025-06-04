# Step 1: Header define karen (optional, agar aap header ko ignore karna chahte hain)
headers = ["ASSOCIATE NAME", "ASSOCIATE ID", "RECEIVER'S NAME", "FORM STATUS", "LINE NO", "SET-NO.OF FORM"]

# Step 2: Data load karne ka function
def load_data(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Pehli line header hai; usko skip ya process karen
        for line in lines[1:]:
            parts = line.strip().split('\t')
            if len(parts) >= 6:
                record = {
                    "associate_name": parts[0],
                    "associate_id": parts[1],
                    "receiver_name": parts[2],
                    "form_status": parts[3],
                    "line_no": parts[4],
                    "set_no": parts[5]
                }
                data.append(record)
    return data

# Step 3: Search filter function
def filter_records(records, search_term):
    search_term = search_term.lower()
    filtered = []
    for rec in records:
        if (search_term in rec["associate_name"].lower() or
            search_term in rec["associate_id"].lower() or
            search_term in rec["receiver_name"].lower()):
            filtered.append(rec)
    return filtered

# Step 4: Results print karne ke liye function
def display_results(results):
    if not results:
        print("No matching records found.")
        return
    print(f"\nTotal {len(results)} matching records:\n")
    for rec in results:
        print(f"Associate Name: {rec['associate_name']}")
        print(f"Associate ID: {rec['associate_id']}")
        print(f"Receiver's Name: {rec['receiver_name']}")
        print(f"Form Status: {rec['form_status']}")
        print(f"Line No: {rec['line_no']}")
        print(f"Set No: {rec['set_no']}")
        print("-" * 50)

# Main program
if __name__ == "__main__":
    filename = 'data.txt'  # aapke data file ka path
    data = load_data(filename)
    search_input = input("Enter search term: ")
    results = filter_records(data, search_input)
    display_results(results)