using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using Microsoft.FluentUI.AspNetCore.Components;
using Blazored.LocalStorage;
using AutoPodcaster;
using AutoPodcaster.Services;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

// Input Service
builder.Services.AddScoped<IInputService, InputService>();
builder.Services.AddKeyedScoped("InputBackend", (sp, key) => new HttpClient { BaseAddress = new Uri(builder.Configuration["InputBackendUrl"] ?? "http://localhost:8081") });

// Subject Space Service
builder.Services.AddScoped<ISubjectSpaceService, SubjectSpaceService>();
builder.Services.AddKeyedScoped("SubjectSpaceBackend", (sp, key) => new HttpClient { BaseAddress = new Uri(builder.Configuration["SubjectSpaceBackendUrl"] ?? "http://localhost:8082") });

builder.Services.AddBlazoredLocalStorage();
builder.Services.AddFluentUIComponents();

await builder.Build().RunAsync();
