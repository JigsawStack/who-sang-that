import requests

def upload_songs():
    # Ask for number of files
    # Hardcoded file data
    file_data = [
        ("audio_clips/danse.mp3", "indila", "danse"),
        ("audio_clips/elevated.mp3", "shubh", "elevated"),
        ("audio_clips/russian_bandana.mp3", "dhanda", "russian bandana"),
        ("audio_clips/stay_with_me.mp3", "miki", "stay with me - mayonakara")
    ]
    
    # Prepare lists for form data
    files = []
    artists = []
    titles = []
    
    # Process all hardcoded files
    for file_path, artist, title in file_data:
        print(f"\nFile: {file_path}")
        print(f"Artist: {artist}")
        print(f"Title: {title}")
        
        # Add file to files list
        files.append(('files', open(file_path, 'rb')))
        artists.append(('artists', artist))
        titles.append(('titles', title))
    
    try:
        # Prepare the data
        data = artists + titles
        
        # Make the POST request
        response = requests.post(
            "http://localhost:8000/ingest-songs",
            files=files,
            data=data
        )
        
        # Close all file handles
        for _, file_obj in files:
            file_obj.close()
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
        # Make sure to close files even if there's an error
        for _, file_obj in files:
            file_obj.close()

if __name__ == "__main__":
    upload_songs()
