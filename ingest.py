import requests

def upload_songs():
    # Ask for number of files
    num_files = int(input("How many files do you want to upload? "))
    
    # Prepare lists for form data
    files = []
    artists = []
    titles = []
    
    # Collect details for each file
    for i in range(num_files):
        print(f"\n--- File {i+1} ---")
        # file_path = input("Enter the file path: ")
        # artist = input("Enter the artist name: ")
        # title = input("Enter the song title: ")
        file_path = "audio_clips/elevated.mp3"
        artist = "Shubh"
        title = "Elevated"
        
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
