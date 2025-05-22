using Microsoft.Maui.Controls.PlatformConfiguration;

namespace MobilUygulama
{
    public partial class MainPage : ContentPage
    {
        

        public MainPage()
        {
            InitializeComponent();

           
        }

        private async Task UploadImageToApi(Stream imageStream, string fileName) //Base64 görseli çizerek ekranda gösterir
        {
            try
            {
                LoadingIndicator.IsRunning = true; //Yükleme animasyonu
                LoadingIndicator.IsVisible = true;
                ErrorLabel.IsVisible = false;
                ErrorStatusLabel.IsVisible = false;

                using var httpClient = new HttpClient(); //HTTP istekleri için HttpClient nesnesi oluşturuyoruz

                var content = new MultipartFormDataContent(); //API'ye görseli multipart/form-data gönderme hazırlığı.  
                var imageContent = new StreamContent(imageStream);
                imageContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");

                content.Add(imageContent, "file", fileName);

                string apiUrl = "http://192.168.136.74:5000/upload";

                var response = await httpClient.PostAsync(apiUrl, content); //API'ye post isteği gönderme
                if (!response.IsSuccessStatusCode)
                {
                    await DisplayAlert("Hata", $"API başarısız oldu: {response.StatusCode}", "Tamam");
                    return;
                }

                var jsonString = await response.Content.ReadAsStringAsync();
                var json = System.Text.Json.JsonDocument.Parse(jsonString);

                var base64Image = json.RootElement.GetProperty("image_base64").GetString(); 
                //Görseli base64 çevirir
                byte[] imageBytes = Convert.FromBase64String(base64Image);
                var memory = new MemoryStream(imageBytes);
                SelectedImage.Source = ImageSource.FromStream(() => new MemoryStream(memory.ToArray()));

            }
            catch (Exception ex)
            {
                await DisplayAlert("Hata", $"Hata oluştu: {ex.Message}", "Tamam");
            }
            finally
            {
                LoadingIndicator.IsRunning = false;
                LoadingIndicator.IsVisible = false;
            }
        }




        private async void OnCapturePhotoClicked(object sender, EventArgs e) //Kameradan fotoğraf çekme
        {
            try
            {
                if (!MediaPicker.Default.IsCaptureSupported)
                {
                    await DisplayAlert("Uyarı", "Bu cihazda kamera desteklenmiyor.", "Tamam");
                    return;
                }

                var photo = await MediaPicker.Default.CapturePhotoAsync();

                if (photo != null)
                {
                    byte[] imageBytes;
                    using (var originalStream = await photo.OpenReadAsync())
                    using (var ms = new MemoryStream())
                    {
                        await originalStream.CopyToAsync(ms);
                        imageBytes = ms.ToArray();
                    }

                    await UploadImageToApi(new MemoryStream(imageBytes), photo.FileName);
                }
            }
            catch (Exception ex)
            {
                await DisplayAlert("Hata", ex.Message, "Tamam");
            }
        }

        private async void OnSelectPhotoClicked(object sender, EventArgs e) //Galeriden fotoğraf çekme
        {
            try
            {
                var result = await FilePicker.PickAsync(new PickOptions
                {
                    PickerTitle = "Bir fotoğraf seçin",
                    FileTypes = FilePickerFileType.Images
                });

                if (result != null)
                {
                    // 1. Orijinal stream'den byte[] oluştur!!
                    byte[] imageBytes;
                    using (var originalStream = await result.OpenReadAsync()) //Seçilen fotoğrafın içeriğini oku
                    using (var ms = new MemoryStream())
                    {
                        await originalStream.CopyToAsync(ms);
                        imageBytes = ms.ToArray();
                    }

                    // Sadece API'ye gönder, gösterme işlemini UploadImageToApi yapacak d,kkat et
                    await UploadImageToApi(new MemoryStream(imageBytes), result.FileName);
                }
            }
            catch (Exception ex)
            {
                await DisplayAlert("Hata", ex.Message, "Tamam");
            }
        }
    }

}