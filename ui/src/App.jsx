import React, { useState, useEffect } from 'react'
import './App.css'
import { GoEyeClosed } from "react-icons/go";
import { RxEyeOpen } from "react-icons/rx";
import { RiDeleteBin6Line } from "react-icons/ri";

const indexerURL = 'http://localhost:8081/';
const subjectURL = 'http://localhost:8082/';
const outputURL = 'http://localhost:8083/';

class knowledgeBaseEntry {
  constructor(entry, request_id = '', status = '', type = '') {
    this.entry = entry;
    this.request_id = request_id;
    this.status = status;
    this.type = type;
  }
}

// 3 states for each output type: 1 = Request, 2 = Processing, 3 = Done
class subjectEntry {
  constructor(subject_id, subject, last_updated) {
    this.subject_id = subject_id;
    this.subject = subject;
    this.last_updated = last_updated;

    this.podcast_id = '';
    this.podcast_status = 1;
    this.podcast_url = '';

    this.blog_id = '';
    this.blog_status = 1;
    this.blog_url = '';

    this.presentation_id = '';
    this.presentation_status = 1;
    this.presentation_url = '';
  }
}

/**
 * The main component of the AutoPodcaster application.
 * 
 * This component handles the following functionalities:
 * - Manages the state of dragging, uploading, knowledge base entries, and subjects.
 * - Retrieves and stores knowledge base entries and subjects in local storage.
 * - Handles text and file submissions for indexing.
 * - Fetches and displays subjects and their associated outputs.
 * - Allows users to add new subjects and delete existing ones.
 * - Provides UI for managing the knowledge space and subject space.
 * 
 * @component
 * @returns {JSX.Element} The rendered component.
 */
function App() {


  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [knowledgeBaseEntries, setKnowledgeBaseEntries] = useState([]);

  useEffect(() => {
    // Retrieve the array from local storage when the component mounts
    const storedItems = localStorage.getItem('knowledgeBaseEntries');
    if (storedItems) {
      setKnowledgeBaseEntries(JSON.parse(storedItems));
    }
    //const storedSubjects = localStorage.getItem('subjects');
    //if (storedSubjects) {
    //  setSubjectEntries(JSON.parse(storedSubjects));
    //}
  }, []);


  //#region Indexer
  const addKnowledgeBaseEntry = (newKnowledgeBaseEntries) => {
    const tmpArray = [...knowledgeBaseEntries, ...newKnowledgeBaseEntries];
    // Store the updated array in local storage
    localStorage.setItem('knowledgeBaseEntries', JSON.stringify(tmpArray));
    setKnowledgeBaseEntries(tmpArray);
  };

  const handleTextIndexSubmit = async (event) => {
    event.preventDefault();
    const dataText = document.getElementById('data-text').value;

    if (dataText.length === 0) {
      return;
    }

    document.getElementById('data-text').disabled = true;
    document.getElementById('data-text').value = 'loading...';

    // Split the dataText by newlines. 
    // And recombine the entries not starting with http, make sure to push the first entry and new entry when previous entry does starts with http
    // example
    // input: line 1. This article is about the history of the internet. 
    //        line 2. It describes the beginnings of the internet and the people who helped create it.
    //        line 3. https://en.wikipedia.org/wiki/History_of_the_Internet
    //        line 4. And this article is about LLMs
    //        line 5. https://en.wikipedia.org/wiki/Large_language_model
    // output: array of 4 elements: [line1+2, line3, line4, line5]

    const dataTextArray = [];
    for (const entry of dataText.split('\n')) {
      if (entry.toLowerCase().startsWith('http')) {
        dataTextArray.push(entry);
      }
      else {
        if (dataTextArray.length === 0 || dataTextArray[dataTextArray.length - 1].toLowerCase().startsWith('http')) {
          dataTextArray.push(entry);
        } else {
          dataTextArray[dataTextArray.length - 1] += '\n' + entry;
        }
      }
    }

    // post each entry to the server
    const resultEntries = [];
    for (const entry of dataTextArray) {
      if (entry.length > 0) {
        try {
          const response = await fetch(indexerURL + 'index', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ input: entry }),
          });

          const result = await response.json();
          if (!result.error) {
            console.log('Success:', 'Request ID:', result.request_id, 'for', entry);
            resultEntries.push(new knowledgeBaseEntry(entry, result.request_id, 'Queued', 'Text'));
          } else {
            console.error('Error:', result.error);
          }
        } catch (error) {
          console.error('Error:', error);
        }
      }
    };
    document.getElementById('data-text').disabled = false;
    document.getElementById('data-text').value = '';

    console.log('number of resultEntries:', resultEntries.length);
    if (resultEntries.length > 0) {
      addKnowledgeBaseEntry(resultEntries);
    }
  }

  const handleInput = (event) => {
    const textarea = event.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 10 * 24)}px`; // 24px is the approximate height of one row
  };

  const handleFileDrop = async (event) => {
    event.preventDefault();
    setDragging(false);
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  };

  const handleFileSelect = async (event) => {
    const files = event.target.files;
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  };

  const uploadFile = async (file) => {

    document.getElementById('file-drop-zone').enabled = false;
    document.getElementById('file-drop-zone').style.backgroundColor = '#f0f0f0';
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(indexerURL + 'index_file', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      const resultEntries = [];
      if (!result.error) {
        console.log('File upload success:', result);
        resultEntries.push(new knowledgeBaseEntry(file.name, result.request_id, 'Queued', 'File'));
        addKnowledgeBaseEntry(resultEntries);
      } else {
        console.error('File upload error:', result.error);
      }
    } catch (error) {
      console.error('File upload error:', error);
    }

    document.getElementById('file-drop-zone').enabled = true;
    document.getElementById('file-drop-zone').style.backgroundColor = '#ffffff';
    setUploading(false);
  }

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleClick = () => {
    document.getElementById('file-input').click();
  };

  const checkIndexerStatus = async (requestId) => {
    try {
      const response = await fetch(indexerURL + 'status/' + requestId);
      const result = await response.json();
      var status;
      console.log('result', result);
      console.log('response.status', response.status);
      if (!result.status) {
        console.error('Error fetching status:', result);
        status = "Error";
      }
      else {
        status = result.status;
      }
      setKnowledgeBaseEntries((prevEntries) =>
        prevEntries.map((entry) =>
          entry.request_id === requestId ? { ...entry, status: status } : entry
        )
      );
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const [isKnowledgeSpaceOpen, setIsKnowledgeSpaceOpen] = useState(true);
  const toggleKnowledgeSpace = () => {
    setIsKnowledgeSpaceOpen(!isKnowledgeSpaceOpen);
  };

  const [isKnowledgeSpaceDetailsOpen, setIsKnowledgeSpaceDetailsOpen] = useState(false);
  const toggleKnowledgeSpaceDetails = () => {
    setIsKnowledgeSpaceDetailsOpen(!isKnowledgeSpaceDetailsOpen);
  };
  //#endregion

  //#region Subject Space
  const [subjects, setSubjectEntries] = useState([]);

  const StoreSubjects = () => {
    // Store the updated array in local storage
    localStorage.setItem('subjects', JSON.stringify(subjects));
  };

  useEffect(() => {
    console.log('useEffect');
    fetchSubjects();
  }, []);

  var fetchSubjectIsRunning = false;
  const fetchSubjects = async () => {
    if (fetchSubjectIsRunning) {
      return;
    }
    try {
      fetchSubjectIsRunning = true;
      // first get all subjects
      console.log("fetching subjects");
      console.log("current subjects:", subjects);
      const responseSubject = await fetch(subjectURL + 'subject');
      const resultSubject = await responseSubject.json();
      if (!resultSubject.error) {
        //for each subject, check if there is an output requested
        resultSubject.forEach(async (subject) => {
          console.log('get details for subject with id', subject.id);
          try {
            const responseOutput = await fetch(outputURL + 'output/for-subject/' + subject.id);
            const resultOutput = await responseOutput.json();

            if (responseOutput.status === 200) {
              console.log('output result:', resultOutput);
              var podcastOutput = null;
              var presentationOutput = null;
              var blogOutput = null;

              // get the most recent podcast output, if any
              if (resultOutput.filter((output) => output.type === 'podcast').length > 1) {
                console.log('More than one podcast output found for subject:', subject.id);
                // keep the most recent one
                podcastOutput = resultOutput.filter((output) => output.type === 'podcast').sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated))[0];
              }
              else if (resultOutput.filter((output) => output.type === 'podcast').length === 1) {
                console.log('Only one podcast output found for subject:', subject.id);
                podcastOutput = resultOutput.filter((output) => output.type === 'podcast')[0];
              }
              console.log('podcastOutput:', podcastOutput);
              // check in the subjectEntries if the subject already exists, if not add it, if yes update the output status
              console.log('subjectEntries:', subjects);
              if (subjects.filter((entry) => entry.subject_id === subject.id).length === 0) {
                console.log('new entry');
                // new entry
                var newSubjectEntry = new subjectEntry(
                  subject.id,
                  subject.subject,
                  subject.last_updated,
                )
                if (podcastOutput) {
                  newSubjectEntry.podcast_id = podcastOutput.id;
                  newSubjectEntry.podcast_status = 3;
                  newSubjectEntry.podcast_url = podcastOutput.url;
                }


                setSubjectEntries((prevEntries) => [...prevEntries, newSubjectEntry]);
              } else {
                console.log('update entry');
                // update the last_updated field + any other field that might have changed
                // get the subject by id
                const subjectEntry = subjects.filter((entry) => entry.subject_id === subject.id)[0];
                subjectEntry.last_updated = subject.last_updated;
                if (podcastOutput) {
                  subjectEntry.podcast_id = podcastOutput.id;
                  subjectEntry.podcast_status = 3;
                  subjectEntry.podcast_url = podcastOutput.url;
                }

                setSubjectEntries((prevEntries) =>
                  prevEntries.map((entry) =>
                    entry.subject_id === subject.id ? subjectEntry : entry
                  )
                );
              }
              StoreSubjects();
            } else {
              console.error('Error fetching output:', result.error);
            }
          } catch (error) {
            console.error('Error fetching output:', error);
          }
          console.log("done fetching subjects");
          console.log("loaded subjects:", subjects);
        });
      } else {
        console.error('Error fetching subjects:', result.error);
      }
    } catch (error) {
      console.error('Error fetching subjects:', error);
    } finally {
      fetchSubjectIsRunning = false;
    }
    
  };

  var runningAddNewSubject = false;
  const addNewSubject = async (event) => {
    if (runningAddNewSubject) { return; }
    event.preventDefault();
    document.getElementById('btnCreateSubject').textContent = 'Creating...';
    document.getElementById('subject-error').innerText = '';
    const subject = document.getElementById("subject").value;
    console.log('subject:', subject);

    if (subject.length === 0) {
      return;
    }

    try {
      runningAddNewSubject = true;
      const response = await fetch(subjectURL + 'subject', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ subject }),
      });

      const result = await response.json();
      if (response.status === 200) {
        document.getElementById("subject").value = '';

      } else {
        document.getElementById('subject-error').innerText = result.detail;
        console.error('Error creating subject:', result.error);
      }
    } catch (error) {
      document.getElementById('subject-error').innerText = 'Could not create subject because ' + error;
      console.error('Error creating subject:', error);
    } finally {
      runningAddNewSubject = false;
      document.getElementById('btnCreateSubject').textContent = 'Create subject';
    }
    //refresh list
    await fetchSubjects();
  } 

    function formatDate(string){
    var options = { year: 'numeric', month: 'long', day: 'numeric' };
    
    return new Date(string).toLocaleDateString([],options) + ' ' + new Date(string).toLocaleTimeString();
}

  //#endregion
  return (
    <>
      <img src="src/assets/autopodcaster.png" alt="AutoPodcaster logo" style={{ width: '40%' }} />
      
      <h2>My Subjects</h2>

      <div>
        <form onSubmit={addNewSubject}>
          <div>
            <label htmlFor="subject">Enter a subject: </label>
            <input type="text" id="subject" name="subject" required />
            <button id="btnCreateSubject" type="submit">Create Subject</button>
          </div>
          <div id="subject-error" style={{ color: 'red' }}></div>
        </form>
      </div>
      <div>
        {subjects.length > 0 ? (
          <table className="styled-table">
            <thead>
              <tr>
              <td>Podcast</td>
              <td>Subject</td>
                <td>Last Updated</td>
                <td>ID</td>
                <td>&nbsp;</td>
              </tr>
            </thead>
            <tbody>
              {subjects.map((result, index) => (
                <tr key={result.subject_id}>
                  <td>
                    <div id={"pod" + result.subject_id} className="text-left-align">
                      {result.podcast_status === 1 ? (
                        <button id={"pod1-" + result.subject_id} onClick={async (event) => {
                          
                          try {
                            
                            event.currentTarget.textContent = 'Requesting...';
                            //event.currentTarget.disabled = true;
                            console.log("requesting podcast for subject", event.currentTarget.parentElement.id);
                            const response = await fetch(outputURL + 'output/', {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              body: JSON.stringify({ subject_id: result.subject_id, output_type: 'podcast' }),
                            });
                            if (response.status === 200) {
                              const result = await response.json();
                              console.log('Success requesting podcast:', result);

                              // Update the status to Processing
                              setSubjectEntries((prevEntries) =>
                                prevEntries.map((entry) =>
                                  entry.subject_id === result.subject_id ? { ...entry, podcast_status: 2, podcast_id: result.request_id } : entry
                                )
                              );
                              StoreSubjects();
                              console.log('subjects: ', subjects);
                            } else {
                              console.error('Error requesting podcast:', response.statusText);
                            }
                          } catch (error) {
                            console.error('Error requesting podcast:', error);
                          } finally {
                            
                          }
                        }}>Request</button>
                      ) : result.podcast_status === 2 ? (
                        <button id={"pod2-" + result.subject_id} onClick={async (event) => {
                          try {
                            //event.currentTarget.disabled = true;
                            console.log("checking progress for podcast for subject", event.currentTarget.parentElement.id.substring(3));
                            // button target
                            const button = document.getElementById("pod2-" + event.currentTarget.parentElement.id.substring(3));
                            console.log('button:', button);
                            console.log('button text:', button.textContent);

                            // get the id of the podcast request
                            if (subjects.filter((entry) => entry.subject_id === result.subject_id).length > 0) {
                              const request_id = subjects.filter((entry) => entry.subject_id === result.subject_id)[0].podcast_id;
                              console.log('request_id:', request_id);

                              const response = await fetch(outputURL + 'status/' + request_id, {
                                method: 'GET'
                              });

                              if (response.status === 200) {
                                const resultStatus = await response.json();
                                console.log('Success checking progress for podcast:', resultStatus);
                                if (resultStatus.status === 'Queued') {
                                  console.log('Podcast still in queue');
                                  if (!button.textContent.startsWith('Queued')) {
                                    button.textContent = 'Queued';
                                  } else {
                                    button.textContent = button.textContent + '.';
                                  }
                                }
                                else if (resultStatus.status === 'Processing') {
                                  console.log('Podcast being processed.');
                                  if (!button.textContent.startsWith('Processing')) {
                                    button.textContent = 'Processing';
                                  } else {
                                    button.textContent = button.textContent + '.';
                                  }
                                }
                                else if (resultStatus.status === 'Saved') {
                                  console.log('Podcast is ready');
                                  // Update the status to Ready
                                  setSubjectEntries((prevEntries) =>
                                    prevEntries.map((entry) =>
                                      entry.subject_id === result.subject_id ? { ...entry, podcast_status: 3 } : entry
                                    )
                                  );
                                  // get the subject of result.subject_id
                                  console.log('result subject:', result.subject_id)
                                  console.log('subject:', subjects);

                                  StoreSubjects();
                                }
                                else {
                                  console.error('Unexpected status:', resultStatus.status);
                                }
                              }
                              else {
                                console.error('Error checking progress for podcast:', response.statusText);
                              }
                            }
                            else {
                              console.error('Error checking progress for podcast:', 'No podcast request found');
                            }
                          } catch (error) {
                            console.error('Error requesting podcast:', error);
                          } finally {
                            //event.currentTarget.enabled = true;
                          }
                        }}>Queued</button>
                      ) : <a href={result.podcast_url} target="_blank" rel="noopener noreferrer">Download</a>}
                    </div>
                  </td>
                  <td><div className="text-left-align">{result.subject}</div></td>
                  <td><div className="text-left-align">{formatDate(result.last_updated)}</div></td>
                  <td><div className="text-left-align">{result.subject_id}</div></td>
                  <td><div id={"sub" + result.subject_id} >
                    <button onClick={async (event) => {
                    try {
                      var idToDelete = event.currentTarget.parentElement.id.substring(3);
                      console.log("deleting the subject", idToDelete);
                      const response = await fetch(subjectURL + 'subject/' + idToDelete, {
                        method: 'DELETE',
                      });
                
                      const result = await response.json();
                      if (!result.error) {
                        setSubjectEntries((prevSubjects) => prevSubjects.filter((subject) => subject.subject_id !== idToDelete));
                      } else {
                        console.error('Error deleting subject:', result.error);
                      }
                    } catch (error) {
                      console.error('Error deleting subject:', error);
                    }
                  }}><RiDeleteBin6Line /></button></div></td>
                </tr>
              ))}
            </tbody>
          </table>) : (
          <p>&nbsp;</p>
        )}
      </div>

      <hr />
      <h2 onClick={toggleKnowledgeSpace}>My Knowledge Space &nbsp;
        <GoEyeClosed style={{ display: isKnowledgeSpaceOpen ? 'none' : 'inline' }} />
        <RxEyeOpen style={{ display: isKnowledgeSpaceOpen ? 'inline' : 'none' }} />
      </h2>
      <div id="knowledge-space"
        style={{
          maxHeight: isKnowledgeSpaceOpen ? '0' : '10000px',
          overflow: 'hidden',
          transition: 'max-height 0.5s ease-out',
        }}
      >
        <form onSubmit={handleTextIndexSubmit}>
          <div
            id='file-drop-zone'
            onDrop={handleFileDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={handleClick}
            style={{
              border: dragging ? '2px dashed #000' : '2px dashed #ccc',
              padding: '20px',
              marginTop: '10px',
              textAlign: 'center',
            }}
          >
            {uploading ? 'Uploading...' : dragging ? 'Drop the PDF or Word file here...' : 'Drag and drop a PDF or Word file here, or click to select a file'}
          </div>
          <input
            id="file-input"
            type="file"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          or<br />
          <textarea
            id="data-text"
            rows="2"
            cols="75"
            placeholder="Paste URL or text here... One URL per line"
            onInput={handleInput}
            style={{ overflow: 'hidden', maxHeight: '240px' }} // 10 rows * 24px
          ></textarea>
          <br />
          <button type="submit">Add to my knowledge space</button>
        </form>
        <br />
        <button onClick={toggleKnowledgeSpaceDetails}>
          {isKnowledgeSpaceDetailsOpen ? 'Hide' : 'Show'} More Details
        </button>
        <div id="knowledge-space-details"
          style={{
            maxHeight: isKnowledgeSpaceDetailsOpen ? '50000px' : '0',
            overflow: 'hidden',
            transition: 'max-height 0.5s ease-out',
          }}>
          <hr />

          {knowledgeBaseEntries.length > 0 && (
            <table className="styled-table">
              <thead>
                <tr>
                  <td>Status</td>
                  <td>Request ID</td>
                  <td>Entry</td>
                  <td>Type</td>
                </tr>
              </thead>
              <tbody>
                {knowledgeBaseEntries.map((result, index) => (
                  <tr key={result.request_id}>
                    <td><div className="text-left-align">{result.status}</div></td>
                    <td><div className="text-left-align">
                      <a href="#" onClick={() => checkIndexerStatus(result.request_id)}>
                        {result.request_id}
                      </a>
                    </div></td>
                    <td><div className="single-line-ellipsis">{result.entry}</div></td>
                    <td><div className="text-left-align">{result.type}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}

export default App;
