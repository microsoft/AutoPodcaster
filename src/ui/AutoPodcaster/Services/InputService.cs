using AutoPodcaster.Models;
using System.Net.Http.Json;

namespace AutoPodcaster.Services;

public class InputService([FromKeyedServices("InputBackend")] HttpClient http) : IInputService
{

	public async Task<IQueryable<Input>> GetInputsAsync()
	{
		// Implementation for GetInputsAsync
		return (await http.GetFromJsonAsync<Input[]>("inputs") ?? []).AsQueryable();
    // return await http.GetStringAsync("inputs");
	}
  
  /// <summary>
  /// Represents the content of an input to be send
  /// to the backend to index a webpage (URL) or
  /// a note (plain text).
  /// </summary>
  /// <param name="input">The input string.</param>
  private class InputContent(string input)
  {
    public string input { get; set; } = input;
  }

	public async Task IndexInputAsync(string input)
	{
		var content = JsonContent.Create(new InputContent(input));
    
		await http.PostAsync("index", content);
	}

	public async Task IndexFileInputAsync(string fileName, FileInfo file, string contentType) {
		var content = new MultipartFormDataContent();
		content.Add(new StreamContent(file.OpenRead()), "file", fileName);
		await http.PostAsync("index_file", content);
	}
}