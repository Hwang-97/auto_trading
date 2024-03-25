import axios from 'axios';
const baseURL = 'http://localhost:5657';
const createApi = axios.create({
  baseURL,
});
let api = {
    getClientIP : async ()=>{
        try {
            const response = await createApi.get('/getClientIP');
            if (response && response.data && response.data.ip) {
              return response.data.ip;
            } else {
              throw new Error('Failed to get client IP');
            }
          } catch (error) {
            throw new Error('Failed to get client IP');
          }
    },
    checkAuthentication: async () => {
      try{
          console.log("checkAuthentication");
      }catch(error){
          throw new Error('Failed to checkAuthentication');
      }
    }
}
export default api;